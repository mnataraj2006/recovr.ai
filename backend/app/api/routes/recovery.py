import hmac
import hashlib
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
from app.db.connection import get_db
from app.models.transaction import Transaction
from app.config.settings import settings
from app.audit.logger import log_audit_event

router = APIRouter()

class WebhookPayloadPayment(BaseModel):
    id: str
    amount: int  # in paise
    status: str
    error_code: str
    error_description: str

class WebhookPayload(BaseModel):
    payment: WebhookPayloadPayment

class WebhookRequest(BaseModel):
    event: str
    event_id: Optional[str] = None
    payload: WebhookPayload

def verify_webhook_signature(body_bytes: bytes, signature_header: Optional[str], timestamp_header: Optional[str]) -> bool:
    """Validates HMAC SHA-256 webhook signature and timestamp freshness."""
    if not signature_header:
        return False
        
    secret = settings.WEBHOOK_SECRET.encode('utf-8')
    
    # Check timestamp freshness if header present (5 minute window)
    if timestamp_header:
        try:
            ts = float(timestamp_header)
            if abs(time.time() - ts) > 300:
                return False
            payload_to_sign = f"{timestamp_header}.".encode('utf-8') + body_bytes
        except ValueError:
            payload_to_sign = body_bytes
    else:
        payload_to_sign = body_bytes

    expected_sig = hmac.new(secret, payload_to_sign, hashlib.sha256).hexdigest()
    
    # Also support raw body hmac match
    raw_expected = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(expected_sig, signature_header) or hmac.compare_digest(raw_expected, signature_header)

@router.post("/webhooks/payment")
async def handle_payment_webhook(
    request: Request,
    req: WebhookRequest,
    db = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp")
):
    sig = x_webhook_signature or x_signature
    body_bytes = await request.body()

    # In production, signature verification is mandatory
    if settings.ENVIRONMENT.lower() == "production" or sig is not None:
        if not verify_webhook_signature(body_bytes, sig, x_timestamp):
            await log_audit_event(
                transaction_id="SECURITY",
                event_type="WEBHOOK_REJECTED",
                actor="SYSTEM",
                source="WebhookRouter",
                reason="Rejected webhook request due to invalid or missing HMAC signature.",
                metadata={"event": req.event, "has_signature": sig is not None}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing webhook signature."
            )

    # 1. Idempotency Check
    event_identifier = req.event_id or f"evt_{req.payload.payment.id}_{req.event}"
    existing_evt = await db["webhook_events"].find_one({"event_id": event_identifier})
    if existing_evt:
        return {
            "received": True,
            "idempotent": True,
            "info": f"Event {event_identifier} already processed."
        }

    # Verify it is a payment.failed event
    if req.event != "payment.failed":
        await db["webhook_events"].insert_one({"event_id": event_identifier, "status": "IGNORED", "created_at": time.time()})
        return {"received": True, "info": "Ignored non-failure event"}
        
    payment = req.payload.payment
    
    # 2. Locate the linked payment record to find transaction_id
    payment_record = await db["payments"].find_one({"_id": payment.id})
    if not payment_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment.id} reference not found in database."
        )
        
    txn_id = payment_record["transaction_id"]
    
    # 3. Fetch linked Transaction
    txn_doc = await db["transactions"].find_one({"_id": txn_id})
    if not txn_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {txn_id} not found."
        )
        
    txn_doc["id"] = txn_doc.pop("_id")
    txn = Transaction(**txn_doc)
    
    # 4. Transition to DIAGNOSING if not already there
    if txn.status != "DIAGNOSING":
        try:
            txn.transition_to("DIAGNOSING")
            txn_data = txn.model_dump()
            txn_data["_id"] = txn_data.pop("id")
            await db["transactions"].replace_one({"_id": txn_id}, txn_data)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            
    # Mark event recorded for idempotency
    await db["webhook_events"].insert_one({
        "event_id": event_identifier,
        "payment_id": payment.id,
        "transaction_id": txn.id,
        "status": "PROCESSED",
        "processed_at": time.time()
    })

    # Trigger Recovery Service in background
    from app.services.recovery_service import recovery_service
    import asyncio
    task = asyncio.create_task(
        recovery_service.process_failed_payment(
            txn.id,
            error_code=payment.error_code,
            error_description=payment.error_description,
            fast_mode=True
        )
    )
    recovery_service.track_task(task)

    # 5. Log Webhook Ingestion event
    await log_audit_event(
        transaction_id=txn.id,
        event_type="WEBHOOK_INGESTED",
        actor="SYSTEM",
        source="WebhookRouter",
        reason=f"Successfully processed failed payment callback from gateway for payment {payment.id}.",
        metadata={
            "event_id": event_identifier,
            "gateway_error_code": payment.error_code,
            "gateway_error_description": payment.error_description
        }
    )
    
    return {
        "received": True,
        "transaction_id": txn.id,
        "recovery_state": txn.status
    }
