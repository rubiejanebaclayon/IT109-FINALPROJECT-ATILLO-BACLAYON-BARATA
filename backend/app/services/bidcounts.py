"""Cached bid counts (pending + accepted bids per gig)."""
from .. import cache, db


def get_bid_counts(gig_ids: list[str]) -> dict[str, int]:
    ids = [str(g) for g in gig_ids]
    cached = cache.mget_json([f"bidcount:{g}" for g in ids])
    result: dict[str, int] = {}
    missing: list[str] = []
    for gid, val in zip(ids, cached):
        if val is None:
            missing.append(gid)
        else:
            result[gid] = int(val)
    if missing:
        rows = db.fetch_all(
            "select gig_id::text as gig_id, count(*) as c from bids "
            "where gig_id = any(%s::uuid[]) and status in ('pending','accepted') group by gig_id",
            (missing,))
        found = {r["gig_id"]: r["c"] for r in rows}
        for gid in missing:
            n = int(found.get(gid, 0))
            result[gid] = n
            cache.set_json(f"bidcount:{gid}", n, cache.TTL_BID_COUNT)
    return result
