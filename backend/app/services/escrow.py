"""Escrow state changes shared by the PayMongo webhook and the manual
"sync payment" button, so both paths behave identically.

Contract state machine:
  pending_payment -> funded -> submitted -> approved -> paid_out
             \\-> cancelled
"""
from psycopg import Connection

from .. import db


def mark_session_paid(session_id: str, payment_id: str | None, conn: Connection) -> dict | None:
    """Mark a PayMongo checkout session as paid and fund the contract.
    Returns contract info only when the state actually changed (so emails are sent once)."""
    pay = db.fetch_one("select * from payments where paymongo_session_id=%s for update", (session_id,), conn)
    if not pay or pay["status"] == "paid":
        return None
    contract = db.fetch_one("select * from contracts where id=%s for update", (pay["contract_id"],), conn)
    db.execute("update payments set status='paid', paid_at=now(), paymongo_payment_id=%s where id=%s",
               (payment_id, pay["id"]), conn)
    if contract["status"] != "pending_payment":
        return None
    db.execute("update contracts set status='funded', funded_at=now() where id=%s", (contract["id"],), conn)
    db.audit(None, "payment.paid", "contracts", contract["id"], {"session": session_id}, conn)
    return contract
