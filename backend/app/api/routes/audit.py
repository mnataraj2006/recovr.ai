from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.db.connection import get_db

router = APIRouter()

@router.get("/audit-events")
async def get_audit_events(
    transaction_id: Optional[str] = Query(None, description="Filter by transaction ID"),
    event_type: Optional[str] = Query(None, description="Filter by audit event type"),
    actor: Optional[str] = Query(None, description="Filter by event actor"),
    limit: int = Query(50, ge=1, le=100, description="Max number of events to return"),
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    db = Depends(get_db)
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
async def get_transaction_audit(transaction_id: str, db = Depends(get_db)):
    """
    Returns the full, chronological audit trail for a single transaction.
    """
    cursor = db["audit_events"].find({"transaction_id": transaction_id}).sort("timestamp", 1)
    events = await cursor.to_list(length=100)
    
    # Fetch guardrail decisions for additional inline context
    guardrail_cursor = db["guardrail_decisions"].find({"transaction_id": transaction_id}).sort("created_at", 1)
    decisions = await guardrail_cursor.to_list(length=50)
    
    for item in events:
        item["id"] = item.pop("_id")
    for item in decisions:
        item["id"] = item.pop("_id")
        
    return {
        "transaction_id": transaction_id,
        "audit_events": events,
        "guardrail_decisions": decisions
    }
