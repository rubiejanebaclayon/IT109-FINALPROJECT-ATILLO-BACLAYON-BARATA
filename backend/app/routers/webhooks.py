"""PayMongo webhook receiver. Payment status is changed ONLY from verified
PayMongo events (or the PayMongo API in sync-payment), never from the browser."""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from .. import db
from ..ratelimit import rate_limit
from ..services import escrow, paymongo_service
from .contracts import notify_funded

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/paymongo", dependencies=[Depends(rate_limit("webhook", 120, 60))])
async def paymongo_webhook(request: Request, tasks: BackgroundTasks):
    raw = await request.body()
    if not paymongo_service.verify_webhook_signature(raw, request.headers.get("paymongo-signature")):
        raise HTTPException(401, "Invalid signature")
    try:
        event = json.loads(raw)
        event_id = event["data"]["id"]
        attrs = event["data"]["attributes"]
        event_type = attrs["type"]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Malformed event")

    changed = None
    with db.transaction() as conn:
        # Idempotency: PayMongo may retry; each event id is processed once.
        fresh = db.fetch_one(
            "insert into webhook_events (event_id, event_type) values (%s,%s) "
            "on conflict do nothing returning event_id", (event_id, event_type), conn)
        if fresh and event_type == "checkout_session.payment.paid":
            session = attrs["data"]
            payments = (session.get("attributes") or {}).get("payments") or []
            payment_id = payments[0].get("id") if payments else None
            changed = escrow.mark_session_paid(session["id"], payment_id, conn)
    if changed:
        notify_funded(changed, tasks)
    return {"received": True}
