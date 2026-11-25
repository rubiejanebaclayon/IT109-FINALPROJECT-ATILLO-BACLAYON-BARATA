"""Gig Requests: CRUD + cached public listing of APPROVED gigs."""
import hashlib
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from .. import cache, db
from ..ratelimit import rate_limit
from ..schemas import GigIn
from ..security import get_current_user, require_captcha, require_client
from ..services import email_service
from ..services.bidcounts import get_bid_counts
from ..validators import CATEGORIES, is_uuid

router = APIRouter(prefix="/gigs", tags=["Gig Requests"])

SORTS = {  # whitelist: user input only chooses a KEY, never raw SQL
    "newest": "g.created_at desc",
    "deadline": "g.deadline asc",
    "budget_high": "g.budget_max desc",
}


def _admin_emails() -> list[str]:
    return [r["email"] for r in db.fetch_all("select email from users where role='admin' and is_active")]


@router.get("/categories")
def categories():
    return CATEGORIES


@router.get("", dependencies=[Depends(rate_limit("gig-list", 60, 60))])
def list_gigs(q: str | None = Query(None, max_length=80), category: str | None = None,
              sort: str = Query("newest", pattern="^(newest|deadline|budget_high)$"),
              page: int = Query(1, ge=1, le=1000), page_size: int = Query(12, ge=1, le=50)):
    """Public list of approved gigs. Cached; the cache is invalidated by a version
    bump whenever a gig changes (see cache.invalidate_gig_listings)."""
    if category and category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")
    params = {"q": (q or "").strip().lower(), "category": category, "sort": sort,
              "page": page, "page_size": page_size}
    digest = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()
    key = f"gigs:list:v{cache.listing_version()}:{digest}"

    page_data = cache.get_json(key)
    from_cache = page_data is not None
    if page_data is None:
        where, args = ["g.status = 'approved'"], []
        if params["q"]:
            where.append("(lower(g.title) like %s or lower(g.description) like %s)")
            like = f"%{params['q'].replace('%', '').replace('_', '')}%"
            args += [like, like]
        if category:
            where.append("g.category = %s")
            args.append(category)
        clause = " and ".join(where)
        total = db.fetch_one(f"select count(*) c from gig_requests g where {clause}", args)["c"]
        items = db.fetch_all(
            f"""select g.id, g.title, left(g.description, 220) as summary, g.category, g.budget_min,
                       g.budget_max, g.deadline, g.created_at, u.full_name as client_name
                from gig_requests g join users u on u.id = g.client_id
                where {clause} order by {SORTS[sort]} limit %s offset %s""",
            args + [page_size, (page - 1) * page_size])
        page_data = {"items": [{**i, "id": str(i["id"])} for i in items], "total": total}
        cache.set_json(key, page_data, cache.TTL_GIG_LIST)

    counts = get_bid_counts([i["id"] for i in page_data["items"]])
    items = [{**i, "bid_count": counts.get(i["id"], 0)} for i in page_data["items"]]
    return {"items": items, "total": page_data["total"], "page": page, "page_size": page_size,
            "cached": from_cache}


@router.get("/mine")
def my_gigs(user: dict = Depends(require_client)):
    rows = db.fetch_all(
        "select id, title, category, budget_min, budget_max, deadline, status, admin_note, created_at "
        "from gig_requests where client_id=%s order by created_at desc", (user["id"],))
    counts = get_bid_counts([str(r["id"]) for r in rows])
    return [{**r, "bid_count": counts.get(str(r["id"]), 0)} for r in rows]


@router.post("", status_code=201,
             dependencies=[Depends(rate_limit("gig-create", 10, 60))])
def create_gig(body: GigIn, tasks: BackgroundTasks, user: dict = Depends(require_client)):
    gig = db.fetch_one(
        "insert into gig_requests (client_id, title, description, category, budget_min, budget_max, deadline) "
        "values (%s,%s,%s,%s,%s,%s,%s) returning *",
        (user["id"], body.title, body.description, body.category, body.budget_min, body.budget_max, body.deadline))
    db.audit(user["id"], "gig.create", "gig_requests", gig["id"])
    cache.invalidate_gig_listings()
    for email in _admin_emails():
        tasks.add_task(email_service.send_email, email, "New gig awaiting approval", "Gig needs review",
                       [f"{user['full_name']} posted: {gig['title']}"], "Review gigs",
                       email_service.link("/admin/gigs"))
    return gig


@router.get("/{gig_id}")
def get_gig(gig_id: str, user: dict = Depends(get_current_user)):
    if not is_uuid(gig_id):
        raise HTTPException(404, "Gig not found")
    gig = db.fetch_one(
        """select g.*, u.full_name as client_name from gig_requests g
           join users u on u.id = g.client_id where g.id=%s""", (gig_id,))
    if not gig:
        raise HTTPException(404, "Gig not found")
    is_owner = str(gig["client_id"]) == user["id"]
    has_bid = db.fetch_one("select 1 as x from bids where gig_id=%s and freelancer_id=%s", (gig_id, user["id"]))
    if gig["status"] != "approved" and not (is_owner or user["role"] == "admin" or has_bid):
        raise HTTPException(404, "Gig not found")
    gig["bid_count"] = get_bid_counts([gig_id])[gig_id]
    gig["my_bid"] = db.fetch_one(
        "select id, amount, delivery_days, proposal, status from bids where gig_id=%s and freelancer_id=%s",
        (gig_id, user["id"])) if user["role"] == "freelancer" else None
    if not is_owner and user["role"] != "admin":
        gig.pop("admin_note", None)
    return gig


@router.put("/{gig_id}", dependencies=[Depends(rate_limit("gig-update", 20, 60))])
def update_gig(gig_id: str, body: GigIn, user: dict = Depends(require_client)):
    if not is_uuid(gig_id):
        raise HTTPException(404, "Gig not found")
    gig = db.fetch_one("select status from gig_requests where id=%s and client_id=%s", (gig_id, user["id"]))
    if not gig:
        raise HTTPException(404, "Gig not found")
    if gig["status"] not in ("pending_approval", "approved", "rejected"):
        raise HTTPException(409, "This gig can no longer be edited")
    if db.fetch_one("select 1 as x from bids where gig_id=%s and status in ('pending','accepted')", (gig_id,)):
        raise HTTPException(409, "You cannot edit a gig that already has bids")
    row = db.fetch_one(
        """update gig_requests set title=%s, description=%s, category=%s, budget_min=%s, budget_max=%s,
                  deadline=%s, status='pending_approval', admin_note=null
           where id=%s and client_id=%s returning *""",
        (body.title, body.description, body.category, body.budget_min, body.budget_max, body.deadline,
         gig_id, user["id"]))
    db.audit(user["id"], "gig.update", "gig_requests", gig_id)
    cache.invalidate_gig_listings()          # edited gig goes back to moderation => leaves the listing
    cache.invalidate_bid_count(gig_id)
    return row


@router.delete("/{gig_id}", status_code=204)
def delete_gig(gig_id: str, user: dict = Depends(get_current_user)):
    if not is_uuid(gig_id) or user["role"] not in ("client", "admin"):
        raise HTTPException(404, "Gig not found")
    gig = db.fetch_one("select client_id from gig_requests where id=%s", (gig_id,))
    if not gig or (user["role"] == "client" and str(gig["client_id"]) != user["id"]):
        raise HTTPException(404, "Gig not found")
    if db.fetch_one("select 1 as x from contracts where gig_id=%s", (gig_id,)):
        raise HTTPException(409, "A contract exists for this gig, so it cannot be deleted")
    db.execute("delete from gig_requests where id=%s", (gig_id,))
    db.audit(user["id"], "gig.delete", "gig_requests", gig_id)
    cache.invalidate_gig_listings()
    cache.invalidate_bid_count(gig_id)
