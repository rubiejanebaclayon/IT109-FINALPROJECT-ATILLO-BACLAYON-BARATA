
"""Private object storage for portfolio assets using Supabase Storage."""
import uuid
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from ..config import get_settings

MAX_BYTES = 5 * 1024 * 1024
SIGNED_URL_SECONDS = 3600

ALLOWED = {
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ("jpg", b"\xff\xd8\xff"),
    "image/webp": ("webp", b"RIFF"),
    "application/pdf": ("pdf", b"%PDF-"),
}


def _headers(s) -> dict:
    return {
        "Authorization": f"Bearer {s.supabase_service_role_key}",
        "apikey": s.supabase_service_role_key,
    }


def validate_file(content_type: str, data: bytes) -> str:
    if content_type not in ALLOWED:
        raise HTTPException(
            400, "Only PNG, JPG, WEBP images and PDF files are allowed"
        )

    if len(data) > MAX_BYTES:
        raise HTTPException(400, "File is too large (max 5 MB)")

    ext, magic = ALLOWED[content_type]

    if not data.startswith(magic):
        raise HTTPException(400, "File content does not match its type")

    return ext


def upload(user_id: str, content_type: str, data: bytes) -> str:
    """Upload a file privately and return its storage path."""
    s = get_settings()
    ext = validate_file(content_type, data)

    path = f"{user_id}/{uuid.uuid4().hex}.{ext}"
    encoded_path = quote(path, safe="/")

    url = (
        f"{s.supabase_url.rstrip('/')}"
        f"/storage/v1/object/{s.supabase_bucket}/{encoded_path}"
    )

    try:
        r = httpx.post(
            url,
            content=data,
            timeout=30.0,
            headers={
                **_headers(s),
                "Content-Type": content_type,
                "x-upsert": "false",
            },
        )
        r.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(
            502, "Could not store the file. Please try again."
        )

    return path


def create_signed_url(
    path: str, expires_in: int = SIGNED_URL_SECONDS
) -> str:
    """Create a temporary URL for an authorized portfolio file."""
    s = get_settings()
    encoded_path = quote(path, safe="/")

    url = (
        f"{s.supabase_url.rstrip('/')}"
        f"/storage/v1/object/sign/{s.supabase_bucket}/{encoded_path}"
    )

    try:
        r = httpx.post(
            url,
            json={"expiresIn": expires_in},
            timeout=15.0,
            headers=_headers(s),
        )
        r.raise_for_status()

        signed_url = r.json().get("signedURL")

        if not signed_url:
            raise ValueError("Supabase did not return a signed URL")

        if signed_url.startswith("http://") or signed_url.startswith("https://"):
            return signed_url

        if signed_url.startswith("/storage/v1/"):
            return f"{s.supabase_url.rstrip('/')}{signed_url}"

        if signed_url.startswith("/"):
            return f"{s.supabase_url.rstrip('/')}/storage/v1{signed_url}"

        return f"{s.supabase_url.rstrip('/')}/storage/v1/{signed_url}"

    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(
            502, "Could not generate a portfolio file link. Please try again."
        )


def remove(path: str) -> None:
    """Delete a file from private Supabase Storage."""
    s = get_settings()

    try:
        httpx.request(
            "DELETE",
            f"{s.supabase_url.rstrip('/')}/storage/v1/object/{s.supabase_bucket}",
            json={"prefixes": [path]},
            timeout=15.0,
            headers=_headers(s),
        )
    except Exception:  # noqa: BLE001
        pass
