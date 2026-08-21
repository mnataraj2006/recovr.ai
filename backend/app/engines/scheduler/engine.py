import asyncio
import random
import logging
from datetime import datetime, timezone
from httpx import AsyncClient
from app.db.connection import get_db
from app.models.transaction import Transaction
from app.audit.logger import log_audit_event

logger = logging.getLogger(__name__)

# Backoff configuration parameters
BASE_DELAY = 10.0
MAX_DELAY = 60.0

class RetryScheduler:
    async def schedule_retry(self, action_id: str, fast_mode: bool = False) -> float:
        """
        Calculates exponential backoff delay and schedules the payment retry
        to run asynchronously in the background.
        """
        db = await get_db()
        
        # 1. Fetch action
        action_doc = await db["recovery_actions"].find_one({"_id": action_id})
        if not action_doc:
            raise ValueError(f"Recovery action {action_id} not found.")
            
        txn_id = action_doc["transaction_id"]
        
        # 2. Fetch Transaction
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        txn_doc["id"] = txn_doc.pop("_id")
        txn = Transaction(**txn_doc)
        
        # Ensure state is APPROVED
        if txn.status != "APPROVED":
            raise ValueError(f"Transaction {txn_id} is in status {txn.status}, not APPROVED.")

        # 3. Calculate attempts to configure delay
        failed_attempts = await db["payment_attempts"].count_documents({
            "transaction_id": txn_id,
            "status": "Failed"
        })
        attempt = failed_attempts  # 0-indexed attempt count

        # 4. Calculate delay: min(MAX_DELAY, BASE_DELAY * 2^attempt) + jitter
        if fast_mode:
            # Shortened delay for pytest execution speed
            delay = 0.1
        else:
            base = min(MAX_DELAY, BASE_DELAY * (2.0 ** attempt))
            jitter = random.uniform(-2.0, 2.0)
            delay = max(0.1, base + jitter)
            
        # 5. Transition transaction status: APPROVED -> EXECUTED
        txn.transition_to("EXECUTED")
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": txn_id}, txn_data)
        
        # Update recovery action status: -> EXECUTING
        await db["recovery_actions"].update_one(
            {"_id": action_id},
            {"$set": {"status": "EXECUTING", "executed_at": datetime.now(timezone.utc)}}
        )
        
        await log_audit_event(
            transaction_id=txn_id,
            event_type="RECOVERY_ACTION_EXECUTED",
            actor="SYSTEM",
            source="RetryScheduler",
            reason=f"Background payment retry scheduled with delay {delay:.2f}s (Attempt count: {failed_attempts + 1}).",
            metadata={"action_id": action_id, "delay": delay, "attempt": failed_attempts + 1}
        )

        # 6. Spawn non-blocking background task to run the retry after delay
        # Pass fast_mode to skip waiting in tests
        task = asyncio.create_task(self._execute_payment_retry_task(txn_id, delay))
        from app.services.recovery_service import recovery_service
        recovery_service.track_task(task)
        
        return delay

    async def _execute_payment_retry_task(self, transaction_id: str, delay: float):
        """Task executing in background after sleep delay."""
        try:
            await asyncio.sleep(delay)
            db = await get_db()
            
            # double check transaction state before initiating retry charge
            txn_doc = await db["transactions"].find_one({"_id": transaction_id})
            if not txn_doc or txn_doc["status"] != "EXECUTED":
                logger.warning(f"Scheduler: Bypassing retry execution. Transaction {transaction_id} is in status {txn_doc.get('status') if txn_doc else 'deleted'}")
                return

            logger.info(f"Scheduler: Executing background retry for Transaction {transaction_id}")
            
            # Simulate a successful payment retry to recover the revenue
            # In a live environment, this would call the payment provider.
            # We call the payments router directly to charge and authorize.
            from app.api.routes.payments import create_payment_intent, attempt_payment, PaymentCreateRequest, PaymentAttemptRequest
            
            # Step A: Create Payment Intent
            create_req = PaymentCreateRequest(transaction_id=transaction_id, payment_method="upi")
            res_create = await create_payment_intent(create_req, db)
            payment_id = res_create["payment_id"]
            
            # Step B: Attempt Authorization (force SUCCESS to recover)
            attempt_req = PaymentAttemptRequest(payment_id=payment_id, simulated_outcome="SUCCESS")
            res_att = await attempt_payment(attempt_req, db)
            
            if res_att.get("success"):
                # Mark the recovery action completed
                await db["recovery_actions"].update_one(
                    {"transaction_id": transaction_id, "status": "EXECUTING"},
                    {"$set": {"status": "SUCCESS"}}
                )
                logger.info(f"Scheduler: Successfully recovered Transaction {transaction_id}")
            else:
                # Mark recovery action failed
                await db["recovery_actions"].update_one(
                    {"transaction_id": transaction_id, "status": "EXECUTING"},
                    {"$set": {"status": "FAILED"}}
                )
                logger.error(f"Scheduler: Background retry failed for Transaction {transaction_id}")
                
        except Exception as e:
            logger.error(f"Scheduler error during background payment retry for txn {transaction_id}: {e}", exc_info=True)

retry_scheduler = RetryScheduler()
