"""Google OAuth 2.0 (authorization-code flow) + JWT session.

1. Frontend shows reCAPTCHA, then sends the browser to  GET /auth/google/login
2. We verify the CAPTCHA, then redirect to Google with a signed `state` value
3. Google redirects back to /auth/google/callback?code=...&state=...
4. We exchange the code, read the verified profile, create/find the user,
   issue our own JWT and redirect to the frontend:  /auth/callback#token=...
"""
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from psycopg.errors import UniqueViolation

from ..schemas import RegisterIn, LoginIn

from .. import db
from ..config import get_settings
from ..ratelimit import client_ip, rate_limit
from ..security import (
    create_access_token,
    create_state_token,
    decode_token,
    get_current_user,
    verify_captcha_token,
    hash_password,
    verify_password,
    require_captcha,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
# ---------------- username/password registration -------------------------
@router.post(
    "/register",
    dependencies=[
        Depends(rate_limit("register", 5, 60)),
        Depends(require_captcha),
    ],
)
def register(data: RegisterIn):
    s = get_settings()
    email = str(data.email).lower()
    username = data.username.lower()

    # Apply the same email-domain restriction as Google registration.
    if s.allowed_domains and email.split("@")[-1] not in s.allowed_domains:
        raise HTTPException(
            status_code=400,
            detail="This email domain is not allowed.",
        )

    password_hash = hash_password(data.password)

    try:
        with db.transaction() as conn:
            user = db.fetch_one(
                """
                INSERT INTO users
                    (email, full_name, role, username, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, full_name, avatar_url, role, is_active
                """,
                (
                    email,
                    data.full_name,
                    data.role,
                    username,
                    password_hash,
                ),
                conn,
            )

            db.execute(
                "INSERT INTO profiles (user_id) VALUES (%s)",
                (user["id"],),
                conn,
            )

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="An account with this email or username already exists.",
        )

    token = create_access_token(str(user["id"]), user["role"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "avatar_url": user["avatar_url"],
            "role": user["role"],
        },
    }


# ---------------- username/password login -------------------------------
@router.post(
    "/login",
    dependencies=[
        Depends(rate_limit("password-login", 10, 60)),
        Depends(require_captcha),
    ],
)
def password_login(data: LoginIn):
    username = data.username.lower()

    user = db.fetch_one(
        """
        SELECT id, email, full_name, avatar_url, role,
               is_active, password_hash
        FROM users
        WHERE LOWER(username) = %s
        """,
        (username,),
    )

    if not user or not user["password_hash"]:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=403,
            detail="Your account has been disabled. Contact the administrator.",
        )

    token = create_access_token(str(user["id"]), user["role"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "avatar_url": user["avatar_url"],
            "role": user["role"],
        },
    }


def _redirect_uri() -> str:
    return f"{get_settings().backend_url.rstrip('/')}/auth/google/callback"


@router.get("/google/login", dependencies=[Depends(rate_limit("login", 15, 60))])
def google_login(request: Request, role: str = Query("client", pattern="^(client|freelancer)$"),
                 captcha_token: str | None = None):
    s = get_settings()
    verify_captcha_token(captcha_token, client_ip(request))
    state = create_state_token({"role": role})
    params = {"client_id": s.google_client_id, "redirect_uri": _redirect_uri(),
              "response_type": "code", "scope": "openid email profile",
              "state": state, "prompt": "select_account"}
    return RedirectResponse(f"{GOOGLE_AUTH}?{urlencode(params)}")


@router.get("/google/callback", dependencies=[Depends(rate_limit("login-cb", 30, 60))])
def google_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    s = get_settings()
    front = s.frontend_url.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{front}/login?error=oauth_cancelled")
    role = decode_token(state, "state").get("role", "client")
    if role not in ("client", "freelancer"):      # admin can never be self-selected
        role = "client"

    try:
        tok = httpx.post(GOOGLE_TOKEN, timeout=15.0, data={
            "code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
            "redirect_uri": _redirect_uri(), "grant_type": "authorization_code"})
        tok.raise_for_status()
        info = httpx.get(GOOGLE_USERINFO, timeout=15.0,
                         headers={"Authorization": f"Bearer {tok.json()['access_token']}"})
        info.raise_for_status()
        g = info.json()
    except Exception:
        return RedirectResponse(f"{front}/login?error=oauth_failed")

    email = (g.get("email") or "").lower()
    if not g.get("email_verified") or not email:
        return RedirectResponse(f"{front}/login?error=email_unverified")
    if s.allowed_domains and email.split("@")[-1] not in s.allowed_domains:
        return RedirectResponse(f"{front}/login?error=domain_not_allowed")

    name = (g.get("name") or email.split("@")[0])[:100]
    with db.transaction() as conn:
        user = db.fetch_one("select id, role, is_active from users where google_sub=%s", (g["sub"],), conn)
        if user is None:
            user = db.fetch_one(
                "insert into users (google_sub, email, full_name, avatar_url, role) "
                "values (%s,%s,%s,%s,%s) returning id, role, is_active",
                (g["sub"], email, name, g.get("picture"), role), conn)
            db.execute("insert into profiles (user_id) values (%s)", (user["id"],), conn)
        else:
            db.execute("update users set avatar_url=%s where id=%s", (g.get("picture"), user["id"]), conn)
    if not user["is_active"]:
        return RedirectResponse(f"{front}/login?error=account_disabled")

    token = create_access_token(str(user["id"]), user["role"])
    return RedirectResponse(f"{front}/auth/callback#token={token}")


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
