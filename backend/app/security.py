"""Authentication (JWT) and role-based access control (RBAC) dependencies."""
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db
from .config import get_settings
from .ratelimit import client_ip

bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


# ---------------- tokens ---------------------------------------------------
def create_access_token(user_id: str, role: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "role": role, "iat": now,
               "exp": now + timedelta(minutes=s.jwt_expire_minutes), "typ": "access"}
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)


def create_state_token(data: dict, minutes: int = 10) -> str:
    """Short-lived signed value used for the OAuth `state` parameter (CSRF protection)."""
    s = get_settings()
    payload = {**data, "typ": "state", "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("typ") != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload


# ---------------- current user + RBAC -------------------------------------
def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(creds.credentials, "access")
    # Always re-read the user: roles and deactivation take effect immediately.
    user = db.fetch_one(
        "select id, email, full_name, avatar_url, role, is_active from users where id = %s",
        (payload["sub"],),
    )
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Account not found or disabled")
    user["id"] = str(user["id"])
    return user


def require_roles(*roles: str):
    """Dependency factory:  Depends(require_roles("client", "admin"))"""

    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to do this")
        return user

    return dependency


require_client = require_roles("client")
require_freelancer = require_roles("freelancer")
require_admin = require_roles("admin")


# ---------------- CAPTCHA (Google reCAPTCHA v2) ---------------------------
def verify_captcha_token(token: str | None, remote_ip: str | None = None) -> None:
    s = get_settings()
    if not s.captcha_enabled:
        return
    if not token:
        raise HTTPException(status_code=400, detail="CAPTCHA is required")
    try:
        r = httpx.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": s.recaptcha_secret_key, "response": token, "remoteip": remote_ip or ""},
            timeout=8.0,
        )

        result = r.json()
        ok = result.get("success") is True

        if not ok:
         print("Google reCAPTCHA error codes:", result.get("error-codes", []))

        
    except Exception:
        raise HTTPException(status_code=503, detail="CAPTCHA service unavailable, try again")
    if not ok:
        raise HTTPException(status_code=400, detail="CAPTCHA verification failed")


def require_captcha(request: Request, x_captcha_token: str | None = Header(default=None)) -> None:
    """Dependency: client must send the reCAPTCHA response in the X-Captcha-Token header."""
    verify_captcha_token(x_captcha_token, client_ip(request))
