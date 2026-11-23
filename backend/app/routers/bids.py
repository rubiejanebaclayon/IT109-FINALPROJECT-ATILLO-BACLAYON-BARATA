"""Bids: freelancers bid on approved gigs; the client reviews and accepts one."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import cache, db
from ..ratelimit import rate_limit
from ..schemas import BidIn
from ..security import get_current_user, require_captcha, require_client, require_freelancer
from ..services import email_service
from ..validators import is_uuid

router = APIRouter(tags=["Bids"])


def _uuid_or_404(value: str, what: str = "Not found"):
    if not is_uuid(value):
        raise HTTPException(404, what)


@router.post("/gigs/{gig_id}/bids", status_code=201,
             dependencies=[Depends(rate_limit("bid-create", 10, 60)), Depends(require_captcha)])
def create_bid(gig_id: str, body: BidIn, tasks: BackgroundTasks, user: dict = Depends(require_freelancer)):
    _uuid_or_404(gig_id, "Gig not found")
    gig = db.fetch_one(
        "select g.id, g.title, g.status, g.client_id, g.budget_max, u.email as client_email "
        "from gig_requests g join users u on u.id=g.client_id where g.id=%s", (gig_id,))
    if not gig or gig["status"] != "approved":
        raise HTTPException(404, "Gig not found or not open for bidding")
    if db.fetch_one("select 1 as x from bids where gig_id=%s and freelancer_id=%s", (gig_id, user["id"])):
        raise HTTPException(409, "You already placed a bid on this gig")
    bid = db.fetch_one(
        "insert into bids (gig_id, freelancer_id, amount, delivery_days, proposal) "
        "values (%s,%s,%s,%s,%s) returning *",
        (gig_id, user["id"], body.amount, body.delivery_days, body.proposal))
    db.audit(user["id"], "bid.create", "bids", bid["id"])
    cache.invalidate_bid_count(gig_id)
    tasks.add_task(email_service.send_email, gig["client_email"], "New bid on your gig", "You received a bid",
                   [f"{user['full_name']} bid PHP {bid['amount']} on '{gig['title']}'."],
                   "Review bids", email_service.link(f"/gigs/{gig_id}"))
    return bid


@router.get("/gigs/{gig_id}/bids")
def list_bids(gig_id: str, user: dict = Depends(get_current_user)):
    _uuid_or_404(gig_id, "Gig not found")
    gig = db.fetch_one("select client_id from gig_requests where id=%s", (gig_id,))
    if not gig or not (user["role"] == "admin" or str(gig["client_id"]) == user["id"]):
        raise HTTPException(404, "Gig not found")
    return db.fetch_all(
        """select b.id, b.amount, b.delivery_days, b.proposal, b.status, b.created_at,
                  u.id as freelancer_id, u.full_name as freelancer_name, u.avatar_url,
                  p.headline, p.skills
           from bids b join users u on u.id=b.freelancer_id
           left join profiles p on p.user_id=u.id
           where b.gig_id=%s and b.status <> 'withdrawn' order by b.created_at""", (gig_id,))


@router.get("/bids/mine")
def my_bids(user: dict = Depends(require_freelancer)):
    return db.fetch_all(
        """select b.id, b.amount, b.delivery_days, b.proposal, b.status, b.created_at,
                  g.id as gig_id, g.title as gig_title, g.status as gig_status,
                  c.id as contract_id
           from bids b join gig_requests g on g.id=b.gig_id
           left join contracts c on c.bid_id=b.id
           where b.freelancer_id=%s order by b.created_at desc""", (user["id"],))


@router.put("/bids/{bid_id}", dependencies=[Depends(rate_limit("bid-update", 20, 60))])
def update_bid(bid_id: str, body: BidIn, user: dict = Depends(require_freelancer)):
    _uuid_or_404(bid_id, "Bid not found")
    row = db.fetch_one(
        "update bids set amount=%s, delivery_days=%s, proposal=%s "
        "where id=%s and freelancer_id=%s and status='pending' returning *",
        (body.amount, body.delivery_days, body.proposal, bid_id, user["id"]))
    if not row:
        raise HTTPException(409, "Only your own pending bids can be edited")
    return row


@router.delete("/bids/{bid_id}", status_code=204)
def delete_bid(bid_id: str, user: dict = Depends(require_freelancer)):
    _uuid_or_404(bid_id, "Bid not found")
    row = db.fetch_one(
        "delete from bids where id=%s and freelancer_id=%s and status='pending' returning gig_id",
        (bid_id, user["id"]))
    if not row:
        raise HTTPException(409, "Only your own pending bids can be withdrawn")
    cache.invalidate_bid_count(str(row["gig_id"]))


@router.post("/bids/{bid_id}/accept", dependencies=[Depends(rate_limit("bid-accept", 10, 60))])
def accept_bid(bid_id: str, tasks: BackgroundTasks, user: dict = Depends(require_client)):
    """Client picks a freelancer: creates the contract (status pending_payment)."""
    _uuid_or_404(bid_id, "Bid not found")
    with db.transaction() as conn:
        bid = db.fetch_one(
            """select b.id, b.gig_id, b.freelancer_id, b.amount, b.status as bid_status,
                      g.client_id, g.status as gig_status, g.title
               from bids b join gig_requests g on g.id=b.gig_id
               where b.id=%s for update of b, g""", (bid_id,), conn)
        if not bid or str(bid["client_id"]) != user["id"]:
            raise HTTPException(404, "Bid not found")
        if bid["gig_status"] != "approved" or bid["bid_status"] != "pending":
            raise HTTPException(409, "This bid can no longer be accepted")
        db.execute("update bids set status='accepted' where id=%s", (bid_id,), conn)
        db.execute("update bids set status='rejected' where gig_id=%s and id<>%s and status='pending'",
                   (bid["gig_id"], bid_id), conn)
        db.execute("update gig_requests set status='awarded' where id=%s", (bid["gig_id"],), conn)
        contract = db.fetch_one(
            "insert into contracts (gig_id, bid_id, client_id, freelancer_id, amount) "
            "values (%s,%s,%s,%s,%s) returning *",
            (bid["gig_id"], bid_id, user["id"], bid["freelancer_id"], bid["amount"]), conn)
        db.audit(user["id"], "bid.accept", "contracts", contract["id"], conn=conn)
    cache.invalidate_gig_listings()
    cache.invalidate_bid_count(str(bid["gig_id"]))
    fl = db.fetch_one("select email from users where id=%s", (bid["freelancer_id"],))
    tasks.add_task(email_service.send_email, fl["email"], "Your bid was accepted!", "Congratulations",
                   [f"{user['full_name']} selected your bid for '{bid['title']}'.",
                    "Work starts once the client funds the escrow."],
                   "Open contract", email_service.link(f"/contracts/{contract['id']}"))
    return contract
