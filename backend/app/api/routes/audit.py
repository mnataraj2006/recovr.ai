from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.db.connection import get_db
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/audit-events")
async def get_audit_events(
    transaction_id: Optional[str] = Query(None, description="Filter by transaction ID"),
    event_type: Optional[str] = Query(None, description="Filter by audit event type"),
    actor: Optional[str] = Query(None, description="Filter by event actor"),
    limit: int = Query(50, ge=1, le=100, description="Max number of events to return"),
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves global structured audit logs with dynamic filtering and pagination.
    """
    filter_query = {}
    if transaction_id:
        filter_query["transaction_id"] = transaction_id
    if event_type:
        filter_query["event_type"] = event_type
    if actor:
        filter_query["actor"] = actor
        
    cursor = db["audit_events"].find(filter_query).sort("timestamp", -1).skip(skip).limit(limit)
    events = await cursor.to_list(length=limit)
    
    # Map _id to id for client representation
    for item in events:
        item["id"] = item.pop("_id")
        
    return events

@router.get("/transactions/{transaction_id}/audit")
async def get_transaction_audit(
    transaction_id: str,
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns the full, chronological audit trail and complete transaction details for a single transaction.
    """
    txn = await db["transactions"].find_one({"_id": transaction_id})
    if txn:
        txn["id"] = str(txn.pop("_id"))

    checkout = None
    customer = None
    if txn and txn.get("checkout_id"):
        chk = await db["checkouts"].find_one({"_id": txn["checkout_id"]})
        if chk:
            chk["id"] = str(chk.pop("_id"))
            checkout = chk
    if txn and txn.get("customer_id"):
        cust = await db["customers"].find_one({"_id": txn["customer_id"]})
        if cust:
            cust["id"] = str(cust.pop("_id"))
            customer = cust

    diagnosis = await db["diagnoses"].find_one({"transaction_id": transaction_id}, sort=[("created_at", -1)])
    if diagnosis:
        diagnosis["id"] = str(diagnosis.pop("_id"))

    action = await db["recovery_actions"].find_one({"transaction_id": transaction_id}, sort=[("created_at", -1)])
    if action:
        action["id"] = str(action.pop("_id"))

    attempts_cursor = db["payment_attempts"].find({"transaction_id": transaction_id}).sort("attempt_number", 1)
    attempts = await attempts_cursor.to_list(length=50)
    for att in attempts:
        att["id"] = str(att.pop("_id"))

    cursor = db["audit_events"].find({"transaction_id": transaction_id}).sort("timestamp", 1)
    events = await cursor.to_list(length=100)
    
    guardrail_cursor = db["guardrail_decisions"].find({"transaction_id": transaction_id}).sort("created_at", 1)
    decisions = await guardrail_cursor.to_list(length=50)
    
    for item in events:
        item["id"] = str(item.pop("_id"))
    for item in decisions:
        item["id"] = str(item.pop("_id"))
        
    return {
        "transaction_id": transaction_id,
        "transaction": txn,
        "checkout": checkout,
        "customer": customer,
        "diagnosis": diagnosis,
        "recovery_action": action,
        "payment_attempts": attempts,
        "audit_events": events,
        "guardrail_decisions": decisions
    }

