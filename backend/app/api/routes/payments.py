import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.db.connection import get_db
from app.models.transaction import Transaction
from app.audit.logger import log_audit_event

router = APIRouter()

class PaymentCreateRequest(BaseModel):
    transaction_id: str
    payment_method: str = "upi"
    upi_provider: Optional[str] = None

class PaymentAttemptRequest(BaseModel):
    payment_id: str
    simulated_outcome: Optional[str] = None  # SUCCESS, INSUFFICIENT_FUNDS, GATEWAY_TIMEOUT, OTP_FAILURE, NETWORK_ERROR, PAYMENT_CANCELLED

class PaymentRetryRequest(BaseModel):
    transaction_id: str
    payment_method: str = "upi"

# Mapping simulated outcomes to gateway error details
OUTCOME_ERRORS = {
    "INSUFFICIENT_FUNDS": {
        "code": "BAD_REQUEST_ERROR",
        "reason": "insufficient_funds",
        "description": "The account balance is insufficient to complete the transaction."
    },
    "GATEWAY_TIMEOUT": {
        "code": "GATEWAY_ERROR",
        "reason": "gateway_timeout",
        "description": "Gateway connection timed out before bank response received."
    },
    "OTP_FAILURE": {
        "code": "BAD_REQUEST_ERROR",
        "reason": "otp_failure",
        "description": "The OTP entered by the user was incorrect or expired."
    },
    "NETWORK_ERROR": {
        "code": "GATEWAY_ERROR",
        "reason": "network_error",
        "description": "A socket connection error occurred during network transit."
    },
    "PAYMENT_CANCELLED": {
        "code": "BAD_REQUEST_ERROR",
        "reason": "payment_cancelled",
        "description": "Payment cancelled by the customer."
    }
}

@router.post("/payments/create", status_code=status.HTTP_201_CREATED)
async def create_payment_intent(req: PaymentCreateRequest, db = Depends(get_db)):
    # 1. Fetch transaction
    txn_doc = await db["transactions"].find_one({"_id": req.transaction_id})
    if not txn_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {req.transaction_id} not found."
        )
    
    # Reconstruct Transaction model
    txn_doc["id"] = txn_doc.pop("_id")
    txn = Transaction(**txn_doc)
    
    # 2. Transition state: -> PAYMENT_ATTEMPTED
    try:
        txn.transition_to("PAYMENT_ATTEMPTED")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # Save back to database
    txn_data = txn.model_dump()
    txn_data["_id"] = txn_data.pop("id")
    await db["transactions"].replace_one({"_id": txn.id}, txn_data)
    
    # 3. Create simulated payment document
    payment_id = f"pay_{uuid.uuid4().hex[:8]}"
    payment_doc = {
        "_id": payment_id,
        "transaction_id": txn.id,
        "payment_method": req.payment_method,
        "upi_provider": req.upi_provider,
        "status": "created",
        "created_at": datetime.now(timezone.utc)
    }
    await db["payments"].insert_one(payment_doc)
    
    # 4. Log audit event
    await log_audit_event(
        transaction_id=txn.id,
        event_type="PAYMENT_ATTEMPTED",
        actor="CUSTOMER",
        source="PaymentsAPI",
        reason="Customer selected payment method and initiated gateway redirect",
        metadata={"payment_id": payment_id, "payment_method": req.payment_method}
    )
    
    return {
        "success": True,
        "payment_id": payment_id,
        "status": "created"
    }

@router.post("/payments/attempt")
async def attempt_payment(req: PaymentAttemptRequest, db = Depends(get_db)):
    # 1. Fetch payment
    payment_doc = await db["payments"].find_one({"_id": req.payment_id})
    if not payment_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {req.payment_id} not found."
        )
    
    txn_id = payment_doc["transaction_id"]
    txn_doc = await db["transactions"].find_one({"_id": txn_id})
    txn_doc["id"] = txn_doc.pop("_id")
    txn = Transaction(**txn_doc)
    
    # Check if transaction is in active state
    if txn.status in ["SUCCESS", "RECOVERED", "UNRECOVERABLE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction is already in terminal state: {txn.status}"
        )

    # 2. Count attempts to determine attempt_number
    prev_attempts = await db["payment_attempts"].count_documents({"transaction_id": txn_id})
    attempt_number = prev_attempts + 1
    payment_attempt_id = f"att_{uuid.uuid4().hex[:8]}"

    # Determine simulated outcome based on transaction's simulated_outcomes array (indexed by prev_attempts),
    # or fallback to req.simulated_outcome, or fallback to GATEWAY_TIMEOUT (never default to SUCCESS blindly).
    outcome = None
    if txn_doc.get("simulated_outcomes"):
        outcomes = txn_doc["simulated_outcomes"]
        if prev_attempts < len(outcomes):
            outcome = outcomes[prev_attempts]
            
    if not outcome and req.simulated_outcome:
        outcome = req.simulated_outcome
        
    if not outcome:
        last_failed = await db["payment_attempts"].find_one(
            {"transaction_id": txn_id, "status": "Failed"},
            sort=[("attempt_number", -1)]
        )
        if last_failed and last_failed.get("gateway_error_code"):
            outcome = last_failed["gateway_error_code"]
        else:
            outcome = "GATEWAY_TIMEOUT"
            
    outcome = outcome.upper()

    if outcome == "SUCCESS":
        action_count = await db["recovery_actions"].count_documents({"transaction_id": txn.id})
        diagnosis_count = await db["diagnoses"].count_documents({"transaction_id": txn.id})
        prev_failed_count = await db["payment_attempts"].count_documents({"transaction_id": txn.id, "status": "Failed"})
        
        is_at_risk = (
            txn.status in ["CHECKOUT_ABANDONED", "DIAGNOSING", "DIAGNOSED", "ACTION_PROPOSED", 
                           "GUARDRAIL_CHECK", "APPROVED", "BLOCKED", "EXECUTING", 
                           "RETRY_ESCALATE", "UNRECOVERABLE"] or
            attempt_number > 1 or
            prev_failed_count > 0 or
            action_count > 0 or
            diagnosis_count > 0
        )
        
        txn.transition_to("SUCCESS")
        if is_at_risk:
            txn.transition_to("RECOVERED")
        
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": txn.id}, txn_data)
        
        # Save payment status update
        await db["payments"].update_one({"_id": req.payment_id}, {"$set": {"status": "authorized"}})
        
        # Save payment_attempts record
        attempt_doc = {
            "_id": payment_attempt_id,
            "transaction_id": txn.id,
            "attempt_number": attempt_number,
            "gateway_reference": f"ref_{uuid.uuid4().hex[:8]}",
            "payment_method": payment_doc["payment_method"],
            "status": "Success",
            "gateway_error_code": None,
            "gateway_error_reason": None,
            "gateway_error_message": None,
            "created_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc)
        }
        await db["payment_attempts"].insert_one(attempt_doc)
        
        # Save recovery outcome document
        outcome_doc = {
            "_id": f"out_{uuid.uuid4().hex[:8]}",
            "transaction_id": txn.id,
            "recovered": True,
            "recovery_method": "RETRY" if attempt_number > 1 else "DIRECT",
            "recovered_at": datetime.now(timezone.utc),
            "amount_recovered": txn.amount,
            "total_cost": 0.0
        }
        await db["recovery_outcomes"].insert_one(outcome_doc)
        
        await log_audit_event(
            transaction_id=txn.id,
            event_type="PAYMENT_RECOVERED" if attempt_number > 1 else "PAYMENT_SUCCESSFUL",
            actor="SYSTEM",
            source="PaymentsAPI",
            reason=f"Payment completed successfully on attempt {attempt_number}.",
            metadata={"payment_id": req.payment_id, "attempt_number": attempt_number}
        )
        
        return {
            "success": True,
            "payment_id": req.payment_id,
            "status": "authorized"
        }
        
    else:
        # Failure Outcome
        if outcome not in OUTCOME_ERRORS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported simulated outcome: {outcome}"
            )
        
        error_details = OUTCOME_ERRORS[outcome]
        
        # Transition state: -> DIAGNOSING (attempt 1) or RETRY_ESCALATE (attempt > 1)
        next_state = "DIAGNOSING" if attempt_number == 1 else "RETRY_ESCALATE"
        txn.transition_to(next_state)
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": txn.id}, txn_data)
        
        # Update payment status
        await db["payments"].update_one({"_id": req.payment_id}, {"$set": {"status": "failed"}})
        
        # Save payment_attempts record
        attempt_doc = {
            "_id": payment_attempt_id,
            "transaction_id": txn.id,
            "attempt_number": attempt_number,
            "gateway_reference": f"ref_{uuid.uuid4().hex[:8]}",
            "payment_method": payment_doc["payment_method"],
            "status": "Failed",
            "gateway_error_code": outcome,
            "gateway_error_reason": error_details["reason"],
            "gateway_error_message": error_details["description"],
            "created_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc)
        }
        await db["payment_attempts"].insert_one(attempt_doc)
        
        await log_audit_event(
            transaction_id=txn.id,
            event_type="PAYMENT_FAILED",
            actor="SYSTEM",
            source="PaymentsAPI",
            reason=f"Payment failed with code {outcome}: {error_details['description']}",
            metadata={
                "payment_id": req.payment_id,
                "attempt_number": attempt_number,
                "error_code": outcome
            }
        )
        
        # Trigger Recovery Service in background after database state is committed
        from app.services.recovery_service import recovery_service
        import asyncio
        task = asyncio.create_task(
            recovery_service.process_failed_payment(
                txn.id,
                error_code=outcome,
                error_description=error_details["description"],
                fast_mode=True
            )
        )
        recovery_service.track_task(task)
        
        # In a real system, this failure webhook triggers our Recovery Loop.
        # We will mock the webhook trigger in Milestone 2 route.
        return {
            "success": False,
            "payment_id": req.payment_id,
            "status": "failed",
            "error": error_details
        }
