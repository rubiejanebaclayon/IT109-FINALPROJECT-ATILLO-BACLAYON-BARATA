"""Contracts & Escrow, deliverable submission, approval and the Gig Ticket Thread."""
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import cache, db
from ..config import get_settings
from ..ratelimit import rate_limit
from ..schemas import SubmissionIn, ThreadMessageIn
from ..security import get_current_user, require_client, require_freelancer
from ..services import email_service, escrow, paymongo_service
from ..validators import is_uuid

router = APIRouter(prefix="/contracts", tags=["Contracts & Escrow"])

CONTRACT_SELECT = """
  select c.id, c.gig_id, c.bid_id, c.amount, c.status, c.funded_at, c.submitted_at, c.approved_at,
         c.created_at, c.client_id, c.freelancer_id,
         g.title as gig_title, g.description as gig_description, g.deadline,
         cu.full_name as client_name, fu.full_name as freelancer_name
  from contracts c
  join gig_requests g on g.id = c.gig_id
  join users cu on cu.id = c.client_id
  join users fu on fu.id = c.freelancer_id
"""


def _load(contract_id: str, user: dict) -> dict:
    """Load a contract and enforce that the caller is a party to it (or an admin)."""
    if not is_uuid(contract_id):
        raise HTTPException(404, "Contract not found")
    c = db.fetch_one(CONTRACT_SELECT + " where c.id=%s", (contract_id,))
    if not c:
        raise HTTPException(404, "Contract not found")
    uid = user["id"]
    if user["role"] != "admin" and uid not in (str(c["client_id"]), str(c["freelancer_id"])):
        raise HTTPException(404, "Contract not found")     # 404 so IDs cannot be probed
    return c


def _email_of(user_id) -> str:
    return db.fetch_one("select email from users where id=%s", (user_id,))["email"]


@router.get("")
def list_contracts(user: dict = Depends(get_current_user)):
    if user["role"] == "admin":
        return db.fetch_all(CONTRACT_SELECT + " order by c.created_at desc limit 200")
    return db.fetch_all(CONTRACT_SELECT + " where c.client_id=%s or c.freelancer_id=%s order by c.created_at desc",
                        (user["id"], user["id"]))


@router.get("/{contract_id}")
def get_contract(contract_id: str, user: dict = Depends(get_current_user)):
    c = _load(contract_id, user)
    c["payment"] = db.fetch_one(
        "select id, status, amount, paid_at, checkout_url from payments where contract_id=%s "
        "order by created_at desc limit 1", (contract_id,))
    c["submissions"] = db.fetch_all(
        "select id, link_url, notes, created_at from submissions where contract_id=%s order by created_at desc",
        (contract_id,))
    c["payout"] = db.fetch_one(
        "select id, status, gross_amount, platform_fee, net_amount, method, reference_no, paid_at "
        "from payouts where contract_id=%s", (contract_id,))
    return c


# ---------------------------- payment (PayMongo sandbox) -------------------
@router.post("/{contract_id}/pay", dependencies=[Depends(rate_limit("pay", 6, 60))])
def start_payment(contract_id: str, user: dict = Depends(require_client)):
    c = _load(contract_id, user)
    if str(c["client_id"]) != user["id"]:
        raise HTTPException(403, "Only the client can pay")
    if c["status"] != "pending_payment":
        raise HTTPException(409, "This contract is not waiting for payment")
    session = paymongo_service.create_checkout_session(contract_id, c["gig_title"], c["amount"])
    with db.transaction() as conn:
        db.execute("update payments set status='expired' where contract_id=%s and status='pending'",
                   (contract_id,), conn)
        db.execute(
            "insert into payments (contract_id, paymongo_session_id, checkout_url, amount) values (%s,%s,%s,%s)",
            (contract_id, session["session_id"], session["checkout_url"], c["amount"]), conn)
    return {"checkout_url": session["checkout_url"]}


@router.post("/{contract_id}/sync-payment", dependencies=[Depends(rate_limit("sync", 12, 60))])
def sync_payment(contract_id: str, tasks: BackgroundTasks, user: dict = Depends(require_client)):
    """Backup for the webhook (handy on localhost): ask PayMongo if the latest session is paid."""
    c = _load(contract_id, user)
    pay = db.fetch_one("select paymongo_session_id from payments where contract_id=%s "
                       "order by created_at desc limit 1", (contract_id,))
    if not pay:
        raise HTTPException(404, "No payment started for this contract")
    paid, payment_id = paymongo_service.retrieve_session_paid(pay["paymongo_session_id"])
    if paid:
        with db.transaction() as conn:
            changed = escrow.mark_session_paid(pay["paymongo_session_id"], payment_id, conn)
        if changed:
            notify_funded(changed, tasks)
    return get_contract(contract_id, user)


def notify_funded(contract: dict, tasks: BackgroundTasks) -> None:
    title = db.fetch_one("select title from gig_requests where id=%s", (contract["gig_id"],))["title"]
    url = email_service.link(f"/contracts/{contract['id']}")
    tasks.add_task(email_service.send_email, _email_of(contract["freelancer_id"]),
                   "Escrow funded - start working", "Contract funded",
                   [f"The client has funded '{title}'. You can start working now."], "Open contract", url)
    tasks.add_task(email_service.send_email, _email_of(contract["client_id"]), "Payment received",
                   "Payment received", [f"Your prepayment for '{title}' is held in escrow."],
                   "Open contract", url)


# ---------------------------- delivery & approval --------------------------
@router.post("/{contract_id}/submit", dependencies=[Depends(rate_limit("submit", 10, 60))])
def submit_work(contract_id: str, body: SubmissionIn, tasks: BackgroundTasks,
                user: dict = Depends(require_freelancer)):
    c = _load(contract_id, user)
    if str(c["freelancer_id"]) != user["id"]:
        raise HTTPException(403, "Only the freelancer on this contract can submit work")
    with db.transaction() as conn:
        locked = db.fetch_one("select status from contracts where id=%s for update", (contract_id,), conn)
        if locked["status"] not in ("funded", "submitted"):
            raise HTTPException(409, "Work can only be submitted after the contract is funded")
        db.execute("insert into submissions (contract_id, link_url, notes) values (%s,%s,%s)",
                   (contract_id, body.link_url, body.notes), conn)
        db.execute("update contracts set status='submitted', submitted_at=now() where id=%s", (contract_id,), conn)
        db.audit(user["id"], "contract.submit", "contracts", contract_id, conn=conn)
    tasks.add_task(email_service.send_email, _email_of(c["client_id"]), "Work submitted for review",
                   "Deliverable ready", [f"{user['full_name']} submitted work for '{c['gig_title']}'."],
                   "Review & approve", email_service.link(f"/contracts/{contract_id}"))
    return get_contract(contract_id, user)


@router.post("/{contract_id}/approve", dependencies=[Depends(rate_limit("approve", 10, 60))])
def approve_work(contract_id: str, tasks: BackgroundTasks, user: dict = Depends(require_client)):
    c = _load(contract_id, user)
    if str(c["client_id"]) != user["id"]:
        raise HTTPException(403, "Only the client can approve")
    fee_pct = get_settings().platform_fee_percent
    with db.transaction() as conn:
        locked = db.fetch_one("select status, amount from contracts where id=%s for update", (contract_id,), conn)
        if locked["status"] != "submitted":
            raise HTTPException(409, "There is no submitted work to approve")
        gross = locked["amount"]
        fee = (gross * Decimal(str(fee_pct)) / 100).quantize(Decimal("0.01"))
        db.execute("update contracts set status='approved', approved_at=now() where id=%s", (contract_id,), conn)
        db.execute("insert into payouts (contract_id, freelancer_id, gross_amount, platform_fee, net_amount) "
                   "values (%s,%s,%s,%s,%s)", (contract_id, c["freelancer_id"], gross, fee, gross - fee), conn)
        db.audit(user["id"], "contract.approve", "contracts", contract_id, conn=conn)
    for admin in db.fetch_all("select email from users where role='admin' and is_active"):
        tasks.add_task(email_service.send_email, admin["email"], "Payout pending", "Payout needs action",
                       [f"Contract '{c['gig_title']}' was approved. Please send the freelancer payout and record it."],
                       "Open payouts", email_service.link("/admin/payouts"))
    tasks.add_task(email_service.send_email, _email_of(c["freelancer_id"]), "Work approved",
                   "Your work was approved", [f"The client approved '{c['gig_title']}'.",
                                              "The admin will send your payout and mark it as paid."],
                   "Open contract", email_service.link(f"/contracts/{contract_id}"))
    return get_contract(contract_id, user)


@router.post("/{contract_id}/cancel")
def cancel_contract(contract_id: str, user: dict = Depends(require_client)):
    """Client can cancel only BEFORE paying (nothing in escrow yet)."""
    c = _load(contract_id, user)
    if str(c["client_id"]) != user["id"]:
        raise HTTPException(403, "Only the client can cancel")
    with db.transaction() as conn:
        n = db.execute("update contracts set status='cancelled' where id=%s and status='pending_payment'",
                       (contract_id,), conn)
        if n == 0:
            raise HTTPException(409, "Only unpaid contracts can be cancelled")
        db.execute("update gig_requests set status='closed' where id=%s", (c["gig_id"],), conn)
        db.audit(user["id"], "contract.cancel", "contracts", contract_id, conn=conn)
    cache.invalidate_gig_listings()
    return get_contract(contract_id, user)


# ---------------------------- Gig Ticket Thread ----------------------------
@router.get("/{contract_id}/thread")
def get_thread(contract_id: str, user: dict = Depends(get_current_user)):
    _load(contract_id, user)
    return db.fetch_all(
        """select m.id, m.body, m.created_at, m.sender_id, u.full_name as sender_name, u.role as sender_role
           from thread_messages m join users u on u.id=m.sender_id
           where m.contract_id=%s order by m.created_at""", (contract_id,))


@router.post("/{contract_id}/thread", status_code=201, dependencies=[Depends(rate_limit("thread", 20, 60))])
def post_thread_message(contract_id: str, body: ThreadMessageIn, tasks: BackgroundTasks,
                        user: dict = Depends(get_current_user)):
    c = _load(contract_id, user)
    if c["status"] == "cancelled":
        raise HTTPException(409, "This contract was cancelled; the thread is closed")
    msg = db.fetch_one("insert into thread_messages (contract_id, sender_id, body) values (%s,%s,%s) "
                       "returning id, body, created_at, sender_id", (contract_id, user["id"], body.body))
    other = c["freelancer_id"] if str(c["client_id"]) == user["id"] else c["client_id"]
    if str(other) != user["id"]:
        tasks.add_task(email_service.send_email, _email_of(other), "New message on your gig ticket",
                       "New ticket message", [f"{user['full_name']} wrote on '{c['gig_title']}'."],
                       "Open ticket", email_service.link(f"/contracts/{contract_id}"))
    return {**msg, "sender_name": user["full_name"], "sender_role": user["role"]}
