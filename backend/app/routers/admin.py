"""Administrator module: gig moderation, users, manual payouts, dashboards."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from .. import cache, db
from ..ratelimit import rate_limit
from ..schemas import PayoutUpdate, RejectIn, UserAdminUpdate
from ..security import get_current_user, require_admin, require_freelancer
from ..services import email_service
from ..services.bidcounts import get_bid_counts
from ..validators import is_uuid

router = APIRouter(tags=["Admin"])


# ---------------------------- gig moderation -------------------------------
@router.get("/admin/gigs")
def admin_gigs(status: str = Query("pending_approval",
                                   pattern="^(pending_approval|approved|rejected|awarded|closed|cancelled|all)$"),
               _: dict = Depends(require_admin)):
    where, args = ("", ()) if status == "all" else ("where g.status = %s", (status,))
    return db.fetch_all(
        f"""select g.id, g.title, g.description, g.category, g.budget_min, g.budget_max, g.deadline,
                   g.status, g.admin_note, g.created_at, u.full_name as client_name, u.email as client_email
            from gig_requests g join users u on u.id=g.client_id {where}
            order by g.created_at desc limit 200""", args)


@router.post("/admin/gigs/{gig_id}/approve")
def approve_gig(gig_id: str, tasks: BackgroundTasks, admin: dict = Depends(require_admin)):
    if not is_uuid(gig_id):
        raise HTTPException(404, "Gig not found")
    row = db.fetch_one(
        "update gig_requests set status='approved', admin_note=null where id=%s and status='pending_approval' "
        "returning id, title, client_id", (gig_id,))
    if not row:
        raise HTTPException(409, "Gig not found or not pending approval")
    db.audit(admin["id"], "gig.approve", "gig_requests", gig_id)
    cache.invalidate_gig_listings()
    cache.invalidate_bid_count(gig_id)
    owner = db.fetch_one("select email from users where id=%s", (row["client_id"],))
    tasks.add_task(email_service.send_email, owner["email"], "Your gig is live", "Gig approved",
                   [f"'{row['title']}' is now visible to freelancers."], "View gig",
                   email_service.link(f"/gigs/{gig_id}"))
    return {"id": gig_id, "status": "approved"}


@router.post("/admin/gigs/{gig_id}/reject")
def reject_gig(gig_id: str, body: RejectIn, tasks: BackgroundTasks, admin: dict = Depends(require_admin)):
    if not is_uuid(gig_id):
        raise HTTPException(404, "Gig not found")
    row = db.fetch_one(
        "update gig_requests set status='rejected', admin_note=%s where id=%s and status='pending_approval' "
        "returning id, title, client_id", (body.reason, gig_id))
    if not row:
        raise HTTPException(409, "Gig not found or not pending approval")
    db.audit(admin["id"], "gig.reject", "gig_requests", gig_id, {"reason": body.reason})
    cache.invalidate_gig_listings()
    owner = db.fetch_one("select email from users where id=%s", (row["client_id"],))
    tasks.add_task(email_service.send_email, owner["email"], "Your gig was not approved", "Gig rejected",
                   [f"'{row['title']}' was rejected.", f"Reason: {body.reason}", "You can edit and resubmit it."],
                   "Edit gig", email_service.link(f"/gigs/{gig_id}"))
    return {"id": gig_id, "status": "rejected"}


# ---------------------------- users ----------------------------------------
@router.get("/admin/users")
def admin_users(role: str | None = Query(None, pattern="^(client|freelancer|admin)$"),
                _: dict = Depends(require_admin)):
    where, args = ("where role = %s", (role,)) if role else ("", ())
    return db.fetch_all(
        f"select id, email, full_name, role, is_active, created_at from users {where} "
        "order by created_at desc limit 500", args)


@router.patch("/admin/users/{user_id}")
def admin_update_user(user_id: str, body: UserAdminUpdate, admin: dict = Depends(require_admin)):
    if not is_uuid(user_id):
        raise HTTPException(404, "User not found")
    if user_id == admin["id"]:
        raise HTTPException(409, "You cannot change your own role or status")
    row = db.fetch_one(
        "update users set is_active = coalesce(%s, is_active), role = coalesce(%s::user_role, role) "
        "where id=%s returning id, email, full_name, role, is_active",
        (body.is_active, body.role, user_id))
    if not row:
        raise HTTPException(404, "User not found")
    db.audit(admin["id"], "user.update", "users", user_id, body.model_dump(exclude_none=True))
    return row


# ---------------------------- payouts (manual) -----------------------------
PAYOUT_SELECT = """
  select p.id, p.contract_id, p.status, p.gross_amount, p.platform_fee, p.net_amount, p.method,
         p.reference_no, p.admin_note, p.paid_at, p.created_at,
         u.full_name as freelancer_name, u.email as freelancer_email, g.title as gig_title
  from payouts p join users u on u.id=p.freelancer_id
  join contracts c on c.id=p.contract_id join gig_requests g on g.id=c.gig_id
"""


@router.get("/admin/payouts")
def admin_payouts(status: str = Query("all", pattern="^(all|pending|processing|paid|failed)$"),
                  _: dict = Depends(require_admin)):
    if status == "all":
        return db.fetch_all(PAYOUT_SELECT + " order by p.created_at desc limit 200")
    return db.fetch_all(PAYOUT_SELECT + " where p.status=%s order by p.created_at desc limit 200", (status,))


@router.put("/admin/payouts/{payout_id}", dependencies=[Depends(rate_limit("payout-update", 30, 60))])
def update_payout(payout_id: str, body: PayoutUpdate, tasks: BackgroundTasks,
                  admin: dict = Depends(require_admin)):
    """The admin records the transfer made OUTSIDE the system (GCash, bank...).
    Nothing here moves money; PayMongo is only used for client prepayments."""
    if not is_uuid(payout_id):
        raise HTTPException(404, "Payout not found")
    with db.transaction() as conn:
        cur = db.fetch_one("select * from payouts where id=%s for update", (payout_id,), conn)
        if not cur:
            raise HTTPException(404, "Payout not found")
        if cur["status"] == "paid":
            raise HTTPException(409, "A payout already marked as paid cannot be changed")
        db.execute(
            """update payouts set status=%s, method=%s, reference_no=%s, admin_note=%s, updated_by=%s,
                      paid_at = case when %s = 'paid' then now() else null end where id=%s""",
            (body.status, body.method, body.reference_no, body.admin_note, admin["id"], body.status, payout_id), conn)
        if body.status == "paid":
            db.execute("update contracts set status='paid_out' where id=%s", (cur["contract_id"],), conn)
        db.audit(admin["id"], "payout.update", "payouts", payout_id, {"status": body.status}, conn)
    row = db.fetch_one(PAYOUT_SELECT + " where p.id=%s", (payout_id,))
    if body.status == "paid":
        tasks.add_task(email_service.send_email, row["freelancer_email"], "You have been paid", "Payout sent",
                       [f"PHP {row['net_amount']} for '{row['gig_title']}' was sent via {row['method']}.",
                        f"Reference: {row['reference_no']}"], "Open contract",
                       email_service.link(f"/contracts/{row['contract_id']}"))
    return row


@router.get("/payouts/mine")
def my_payouts(user: dict = Depends(require_freelancer)):
    return db.fetch_all(PAYOUT_SELECT + " where p.freelancer_id=%s order by p.created_at desc", (user["id"],))


# ---------------------------- dashboards -----------------------------------
def _count(sql: str, args=()) -> int:
    return int(db.fetch_one(sql, args)["c"])


@router.get("/dashboard/client")
def client_dashboard(user: dict = Depends(get_current_user)):
    if user["role"] != "client":
        raise HTTPException(403, "Clients only")
    u = (user["id"],)
    return {
        "gigs_pending": _count("select count(*) c from gig_requests where client_id=%s and status='pending_approval'", u),
        "gigs_open": _count("select count(*) c from gig_requests where client_id=%s and status='approved'", u),
        "bids_received": _count("select count(*) c from bids b join gig_requests g on g.id=b.gig_id "
                                "where g.client_id=%s and b.status='pending'", u),
        "contracts_awaiting_payment": _count("select count(*) c from contracts where client_id=%s and status='pending_payment'", u),
        "contracts_active": _count("select count(*) c from contracts where client_id=%s and status in ('funded','submitted')", u),
        "contracts_to_approve": _count("select count(*) c from contracts where client_id=%s and status='submitted'", u),
    }


@router.get("/dashboard/freelancer")
def freelancer_dashboard(user: dict = Depends(get_current_user)):
    if user["role"] != "freelancer":
        raise HTTPException(403, "Freelancers only")
    u = (user["id"],)
    earned = db.fetch_one("select coalesce(sum(net_amount),0) s from payouts where freelancer_id=%s and status='paid'", u)
    pending = db.fetch_one("select coalesce(sum(net_amount),0) s from payouts where freelancer_id=%s and status<>'paid'", u)
    return {
        "bids_pending": _count("select count(*) c from bids where freelancer_id=%s and status='pending'", u),
        "bids_accepted": _count("select count(*) c from bids where freelancer_id=%s and status='accepted'", u),
        "contracts_active": _count("select count(*) c from contracts where freelancer_id=%s and status in ('funded','submitted')", u),
        "contracts_awaiting_payment": _count("select count(*) c from contracts where freelancer_id=%s and status='pending_payment'", u),
        "portfolio_items": _count("select count(*) c from portfolio_items where user_id=%s", u),
        "earned": earned["s"], "pending_payout": pending["s"],
    }


@router.get("/dashboard/admin")
def admin_dashboard(_: dict = Depends(require_admin)):
    escrow_held = db.fetch_one("select coalesce(sum(amount),0) s from contracts where status in ('funded','submitted','approved')")
    return {
        "users": _count("select count(*) c from users"),
        "gigs_pending_review": _count("select count(*) c from gig_requests where status='pending_approval'"),
        "gigs_approved": _count("select count(*) c from gig_requests where status='approved'"),
        "contracts_funded": _count("select count(*) c from contracts where status in ('funded','submitted')"),
        "payouts_pending": _count("select count(*) c from payouts where status in ('pending','processing')"),
        "payouts_paid": _count("select count(*) c from payouts where status='paid'"),
        "escrow_held": escrow_held["s"],
    }
