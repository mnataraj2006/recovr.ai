import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from app.models.audit import AuditEvent
from app.db.connection import get_db

logger = logging.getLogger(__name__)

async def log_audit_event(
    transaction_id: str,
    event_type: str,
    actor: str,
    source: str,
    reason: str,
    metadata: Dict[str, Any] = None
) -> AuditEvent:
    """
    Appends a new structured audit log event to the MongoDB audit_events collection.
    """
    db = await get_db()
    event = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:8]}",
        transaction_id=transaction_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        actor=actor,
        source=source,
        reason=reason,
        metadata=metadata or {}
    )
    
    doc = event.model_dump()
    doc["_id"] = doc.pop("id")  # Map to MongoDB primary key _id
    
    await db["audit_events"].insert_one(doc)
    logger.info(f"Audit [{event_type}] for Transaction {transaction_id}: {reason}")
    return event
