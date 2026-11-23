"""Caching layer.

* Primary store: Upstash Redis through its REST API (free tier).
* Fallback: a small in-memory TTL cache (approved by the project brief) used
  when Upstash is not configured or temporarily unreachable.

Cache invalidation strategy
---------------------------
1. TTL (expiration): every entry expires automatically (see TTL_* constants).
2. Version key for LISTINGS: the approved-gig list is stored under a key that
   contains a version number ("gigs:list:v7:..."). Whenever a gig is created,
   edited, approved, rejected, awarded or deleted we INCR the version, which
   makes every old list key unreachable at once (no key scanning needed).
3. Direct delete for BID COUNTS: when a bid is created, withdrawn, deleted,
   accepted or rejected we delete "bidcount:<gig_id>".
"""
import json
import threading
import time
from typing import Any

import httpx

from .config import get_settings

TTL_GIG_LIST = 60          # seconds
TTL_BID_COUNT = 120        # seconds
TTL_PSGC = 86400           # address lists rarely change: 1 day

_lock = threading.Lock()
_mem: dict[str, tuple[float | None, str]] = {}   # key -> (expires_at, json string)
_http: httpx.Client | None = None


def _client() -> httpx.Client | None:
    global _http
    s = get_settings()
    if not (s.upstash_redis_rest_url and s.upstash_redis_rest_token):
        return None
    if _http is None:
        _http = httpx.Client(
            base_url=s.upstash_redis_rest_url.rstrip("/"),
            headers={"Authorization": f"Bearer {s.upstash_redis_rest_token}"},
            timeout=3.0,
        )
    return _http


def _redis(*command: Any) -> Any:
    """Send one Redis command to Upstash. Raises on failure."""
    c = _client()
    if c is None:
        raise RuntimeError("redis not configured")
    r = c.post("/", json=[str(x) for x in command])
    r.raise_for_status()
    return r.json().get("result")


# ---------------- in-memory helpers ---------------------------------------
def _mem_get(key: str) -> str | None:
    with _lock:
        item = _mem.get(key)
        if not item:
            return None
        exp, val = item
        if exp is not None and exp < time.time():
            _mem.pop(key, None)
            return None
        return val


def _mem_set(key: str, val: str, ttl: int | None) -> None:
    with _lock:
        _mem[key] = (time.time() + ttl if ttl else None, val)


def _mem_incr(key: str, ttl: int | None = None) -> int:
    with _lock:
        item = _mem.get(key)
        now = time.time()
        if item and (item[0] is None or item[0] >= now):
            n = int(item[1]) + 1
            _mem[key] = (item[0], str(n))
            return n
        _mem[key] = (now + ttl if ttl else None, "1")
        return 1


# ---------------- public API ------------------------------------------------
def get_json(key: str) -> Any | None:
    try:
        if _client():
            raw = _redis("GET", key)
        else:
            raw = _mem_get(key)
    except Exception:
        raw = _mem_get(key)
    return json.loads(raw) if raw else None


def set_json(key: str, value: Any, ttl: int) -> None:
    raw = json.dumps(value, default=str)
    try:
        if _client():
            _redis("SET", key, raw, "EX", ttl)
            return
    except Exception:
        pass
    _mem_set(key, raw, ttl)


def delete(*keys: str) -> None:
    try:
        if _client():
            _redis("DEL", *keys)
    except Exception:
        pass
    with _lock:
        for k in keys:
            _mem.pop(k, None)


def mget_json(keys: list[str]) -> list[Any | None]:
    if not keys:
        return []
    try:
        if _client():
            raws = _redis("MGET", *keys)
            return [json.loads(r) if r else None for r in raws]
    except Exception:
        pass
    return [json.loads(v) if (v := _mem_get(k)) else None for k in keys]


def incr(key: str, ttl: int | None = None) -> int:
    """Atomic counter. With `ttl`, the key expires `ttl` seconds after first use."""
    try:
        if _client():
            n = int(_redis("INCR", key))
            if n == 1 and ttl:
                _redis("EXPIRE", key, ttl)
            return n
    except Exception:
        pass
    return _mem_incr(key, ttl)


# ---------------- listing version (cache invalidation) ----------------------
def listing_version() -> int:
    try:
        if _client():
            v = _redis("GET", "gigs:ver")
            return int(v) if v else 1
    except Exception:
        pass
    v = _mem_get("gigs:ver")
    return int(v) if v else 1


def invalidate_gig_listings() -> None:
    """Call after ANY change that affects what the public listing shows."""
    try:
        if _client():
            _redis("INCR", "gigs:ver")
    except Exception:
        pass
    with _lock:
        cur = int(_mem.get("gigs:ver", (None, "1"))[1])
        _mem["gigs:ver"] = (None, str(cur + 1))


def invalidate_bid_count(gig_id: str) -> None:
    delete(f"bidcount:{gig_id}")
