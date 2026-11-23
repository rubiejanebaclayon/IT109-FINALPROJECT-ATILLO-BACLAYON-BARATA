"""Profiles, Portfolio (object storage) and the PSGC address proxy."""
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from .. import cache, db
from ..ratelimit import rate_limit
from ..schemas import PortfolioUpdate, ProfileUpdate
from ..security import get_current_user, require_freelancer
from ..services import storage_service
from ..validators import is_uuid

router = APIRouter(tags=["Profiles & Portfolio"])
MAX_PORTFOLIO_ITEMS = 12



def _portfolio(user_id: str) -> list[dict]:
    items = db.fetch_all(
        "select id, title, description, storage_path, content_type, created_at "
        "from portfolio_items where user_id=%s order by created_at desc",
        (user_id,),
    )

    for item in items:
        path = item.pop("storage_path")
        item["asset_url"] = storage_service.create_signed_url(path)

    return items



# ------------------------------ profile ------------------------------------
@router.get("/profiles/me")
def my_profile(user: dict = Depends(get_current_user)):
    profile = db.fetch_one("select * from profiles where user_id=%s", (user["id"],)) or {}
    return {"user": user, "profile": profile, "portfolio": _portfolio(user["id"])}


@router.put("/profiles/me", dependencies=[Depends(rate_limit("profile-update", 20, 60))])
def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    with db.transaction() as conn:
        if body.full_name:
            db.execute("update users set full_name=%s where id=%s", (body.full_name, user["id"]), conn)
        db.execute(
            """insert into profiles (user_id, headline, bio, skills, school_or_dept, contact_number,
                 region_code, region_name, province_code, province_name,
                 city_code, city_name, barangay_code, barangay_name)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               on conflict (user_id) do update set
                 headline=excluded.headline, bio=excluded.bio, skills=excluded.skills,
                 school_or_dept=excluded.school_or_dept, contact_number=excluded.contact_number,
                 region_code=excluded.region_code, region_name=excluded.region_name,
                 province_code=excluded.province_code, province_name=excluded.province_name,
                 city_code=excluded.city_code, city_name=excluded.city_name,
                 barangay_code=excluded.barangay_code, barangay_name=excluded.barangay_name""",
            (user["id"], body.headline, body.bio, body.skills, body.school_or_dept, body.contact_number,
             body.region_code, body.region_name, body.province_code, body.province_name,
             body.city_code, body.city_name, body.barangay_code, body.barangay_name), conn)
    return my_profile(user)


@router.get("/profiles/{user_id}")
def public_profile(user_id: str, _: dict = Depends(get_current_user)):
    """Public view: never exposes email or phone number."""
    if not is_uuid(user_id):
        raise HTTPException(404, "Profile not found")
    row = db.fetch_one(
        """select u.id, u.full_name, u.avatar_url, u.role, p.headline, p.bio, p.skills,
                  p.school_or_dept, p.city_name, p.province_name
           from users u left join profiles p on p.user_id=u.id
           where u.id=%s and u.is_active and u.role <> 'admin'""", (user_id,))
    if not row:
        raise HTTPException(404, "Profile not found")
    row["portfolio"] = _portfolio(user_id)
    return row


# ------------------------------ portfolio ----------------------------------
def _validate_form(title: str, description: str | None) -> PortfolioUpdate:
    try:
        return PortfolioUpdate(title=title, description=description)
    except ValidationError as e:
        raise HTTPException(422, [{"msg": err["msg"], "loc": list(map(str, err["loc"]))} for err in e.errors()])


@router.post("/portfolio", status_code=201, dependencies=[Depends(rate_limit("portfolio-upload", 10, 60))])
def add_portfolio_item(title: str = Form(...), description: str | None = Form(None),
                       file: UploadFile = File(...), user: dict = Depends(require_freelancer)):
    item = _validate_form(title, description)
    count = db.fetch_one("select count(*) c from portfolio_items where user_id=%s", (user["id"],))["c"]
    if count >= MAX_PORTFOLIO_ITEMS:
        raise HTTPException(409, f"Portfolio limit reached ({MAX_PORTFOLIO_ITEMS} items)")
    data = file.file.read(storage_service.MAX_BYTES + 1)
    
    path = storage_service.upload(
        user["id"], file.content_type or "", data
    )

    row = db.fetch_one(
        "insert into portfolio_items "
        "(user_id, title, description, storage_path, content_type) "
        "values (%s,%s,%s,%s,%s) "
        "returning id, title, description, storage_path, content_type, created_at",
        (user["id"], item.title, item.description, path, file.content_type),
    )

    row["asset_url"] = storage_service.create_signed_url(
        row.pop("storage_path")
    )

    return row



@router.put("/portfolio/{item_id}")
def update_portfolio_item(item_id: str, body: PortfolioUpdate, user: dict = Depends(require_freelancer)):
    if not is_uuid(item_id):
        raise HTTPException(404, "Item not found")
    row = db.fetch_one(
        "update portfolio_items set title=%s, description=%s where id=%s and user_id=%s "
        "returning id, title, description, asset_url, content_type, created_at",
        (body.title, body.description, item_id, user["id"]))
    if not row:
        raise HTTPException(404, "Item not found")
    return row


@router.delete("/portfolio/{item_id}", status_code=204)
def delete_portfolio_item(item_id: str, user: dict = Depends(require_freelancer)):
    if not is_uuid(item_id):
        raise HTTPException(404, "Item not found")
    row = db.fetch_one("delete from portfolio_items where id=%s and user_id=%s returning storage_path",
                       (item_id, user["id"]))
    if not row:
        raise HTTPException(404, "Item not found")
    storage_service.remove(row["storage_path"])


# ------------------------------ PSGC address API ---------------------------
PSGC = "https://psgc.gitlab.io/api"


def _psgc(path: str) -> list[dict]:
    key = f"psgc:{path}"
    hit = cache.get_json(key)
    if hit is not None:
        return hit
    try:
        r = httpx.get(f"{PSGC}{path}", timeout=15.0)
        r.raise_for_status()
        data = [{"code": x["code"], "name": x["name"]} for x in r.json()]
    except Exception:
        raise HTTPException(502, "Address service is unavailable right now")
    data.sort(key=lambda x: x["name"])
    cache.set_json(key, data, cache.TTL_PSGC)
    return data


def _code(code: str) -> str:
    if not code.isdigit() or not 9 <= len(code) <= 10:
        raise HTTPException(400, "Invalid PSGC code")
    return code


@router.get("/psgc/regions")
def regions():
    return _psgc("/regions.json")


@router.get("/psgc/regions/{code}/provinces")
def provinces(code: str):
    return _psgc(f"/regions/{_code(code)}/provinces.json")


@router.get("/psgc/regions/{code}/cities")          # regions without provinces (e.g. NCR)
def region_cities(code: str):
    return _psgc(f"/regions/{_code(code)}/cities-municipalities.json")


@router.get("/psgc/provinces/{code}/cities")
def province_cities(code: str):
    return _psgc(f"/provinces/{_code(code)}/cities-municipalities.json")


@router.get("/psgc/cities/{code}/barangays")
def barangays(code: str):
    return _psgc(f"/cities-municipalities/{_code(code)}/barangays.json")
