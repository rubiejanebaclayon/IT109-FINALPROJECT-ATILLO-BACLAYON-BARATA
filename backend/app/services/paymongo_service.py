"""PayMongo SANDBOX integration (client prepayment into escrow).

Flow: backend creates a Checkout Session -> client pays on PayMongo's hosted
page -> PayMongo calls our webhook (checkout_session.payment.paid) -> we mark the
payment "paid" and the contract "funded". Payouts to freelancers are NOT done
through PayMongo; the admin records them manually.
"""
import hashlib
import hmac
from decimal import Decimal

import httpx
from fastapi import HTTPException

from ..config import get_settings

API = "https://api.paymongo.com/v1"


def _auth() -> tuple[str, str]:
    key = get_settings().paymongo_secret_key
    if not key.startswith("sk_test_"):
        # Safety guard: this project must only ever use sandbox (test mode) keys.
        raise HTTPException(500, "PayMongo is not configured with a test-mode secret key")
    return key, ""


def create_checkout_session(contract_id: str, title: str, amount: Decimal) -> dict:
    s = get_settings()
    centavos = int((amount * 100).quantize(Decimal("1")))
    body = {"data": {"attributes": {
        "line_items": [{"currency": "PHP", "amount": centavos, "name": title[:100], "quantity": 1}],
        "payment_method_types": ["gcash", "card", "paymaya"],
        "description": f"Escrow prepayment for contract {contract_id}",
        "reference_number": contract_id,
        "send_email_receipt": False,
        "show_description": True,
        "success_url": f"{s.frontend_url.rstrip('/')}/contracts/{contract_id}?paid=1",
        "cancel_url": f"{s.frontend_url.rstrip('/')}/contracts/{contract_id}?paid=0",
    }}}
    try:
        r = httpx.post(f"{API}/checkout_sessions", json=body, auth=_auth(), timeout=20.0)
    except httpx.HTTPError:
        raise HTTPException(502, "Payment service unreachable")
    if r.status_code >= 300:
        raise HTTPException(502, "Payment service rejected the request")
    data = r.json()["data"]
    return {"session_id": data["id"], "checkout_url": data["attributes"]["checkout_url"]}


def retrieve_session_paid(session_id: str) -> tuple[bool, str | None]:
    """Ask PayMongo directly whether a session is paid. Returns (is_paid, payment_id)."""
    try:
        r = httpx.get(f"{API}/checkout_sessions/{session_id}", auth=_auth(), timeout=20.0)
    except httpx.HTTPError:
        raise HTTPException(502, "Payment service unreachable")
    if r.status_code >= 300:
        raise HTTPException(502, "Could not verify the payment")
    attrs = r.json()["data"]["attributes"]
    for p in attrs.get("payments") or []:
        if (p.get("attributes") or {}).get("status") == "paid":
            return True, p.get("id")
    intent = attrs.get("payment_intent") or {}
    if (intent.get("attributes") or {}).get("status") == "succeeded":
        return True, None
    return False, None


def verify_webhook_signature(raw_body: bytes, header: str | None) -> bool:
    """PayMongo header looks like:  t=1700000000,te=<test sig>,li=<live sig>
    signature = HMAC-SHA256(secret, f"{t}.{raw_body}")"""
    secret = get_settings().paymongo_webhook_secret
    if not secret or not header:
        return False
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    timestamp = parts.get("t")
    if not timestamp:
        return False
    signed = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    # We only accept TEST-mode signatures (te); live signatures (li) are ignored.
    provided = parts.get("te", "")
    return hmac.compare_digest(expected, provided)
