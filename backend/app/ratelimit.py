"""Rate limiting (fixed window counter stored in Upstash Redis or memory)."""
import time

from fastapi import HTTPException, Request

from . import cache
from .config import get_settings


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_limit(scope: str, identity: str, limit: int, window: int) -> None:
    """Raise HTTP 429 when `identity` exceeded `limit` requests in `window` seconds."""
    bucket = int(time.time() // window)
    key = f"rl:{scope}:{identity}:{bucket}"
    count = cache.incr(key, ttl=window + 1)
    if count > limit:
        retry = window - int(time.time() % window)
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down and try again shortly.",
            headers={"Retry-After": str(retry)},
        )


def rate_limit(scope: str, limit: int, window: int = 60):
    """Dependency factory:  Depends(rate_limit("bid-create", 10, 60))"""

    def dependency(request: Request) -> None:
        check_limit(scope, client_ip(request), limit, window)

    return dependency
