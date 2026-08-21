from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.db.connection import get_db
from app.models.transaction import Transaction
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
    payload: WebhookPayload

@router.post("/webhooks/payment")
async def handle_payment_webhook(req: WebhookRequest, db = Depends(get_db)):
    # Verify it is a payment.failed event
    if req.event != "payment.failed":
        return {"received": True, "info": "Ignored non-failure event"}
        
    payment = req.payload.payment
    
    # 1. Locate the linked payment record to find transaction_id
    payment_record = await db["payments"].find_one({"_id": payment.id})
    if not payment_record:
        # Fallback: Check if we have transaction directly matching in description or order_id
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment.id} reference not found in database."
        )
        
    txn_id = payment_record["transaction_id"]
    
    # 2. Fetch linked Transaction
    txn_doc = await db["transactions"].find_one({"_id": txn_id})
    if not txn_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {txn_id} not found."
        )
        
    txn_doc["id"] = txn_doc.pop("_id")
    txn = Transaction(**txn_doc)
    
    # 3. Transition to DIAGNOSING if not already there
    if txn.status != "DIAGNOSING":
        try:
            txn.transition_to("DIAGNOSING")
            txn_data = txn.model_dump()
            txn_data["_id"] = txn_data.pop("id")
            await db["transactions"].replace_one({"_id": txn_id}, txn_data)
        except ValueError as e:
            # If transition fails, raise bad request
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            
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

    # 4. Log Webhook Ingestion event
    await log_audit_event(
        transaction_id=txn.id,
        event_type="WEBHOOK_INGESTED",
        actor="SYSTEM",
        source="WebhookRouter",
        reason=f"Successfully processed failed payment callback from gateway for payment {payment.id}.",
        metadata={
            "gateway_error_code": payment.error_code,
            "gateway_error_description": payment.error_description
        }
    )
    
    return {
        "received": True,
        "transaction_id": txn.id,
        "recovery_state": txn.status
    }
