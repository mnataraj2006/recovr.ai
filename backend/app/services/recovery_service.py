import logging
from datetime import datetime, timezone
from app.engines.diagnosis.engine import diagnosis_engine
from app.engines.policy.engine import policy_engine
from app.engines.guardrails.engine import guardrail_engine
from app.engines.scheduler.engine import retry_scheduler
from app.audit.logger import log_audit_event
from app.db.connection import get_db

import asyncio

logger = logging.getLogger(__name__)

class RecoveryService:
    def __init__(self):
        self.active_tasks = []

    def track_task(self, task: asyncio.Task):
        self.active_tasks.append(task)
        # Clean up done tasks
        self.active_tasks = [t for t in self.active_tasks if not t.done()]

    async def wait_for_pending_tasks(self):
        # Loop to gather any child tasks spawned during execution of parent tasks
        while True:
            tasks = [t for t in self.active_tasks if not t.done()]
            if not tasks:
                break
            logger.info(f"RecoveryService: Awaiting {len(tasks)} pending background tasks.")
            await asyncio.gather(*tasks, return_exceptions=True)
        self.active_tasks = []
    async def process_failed_payment(self, transaction_id: str, error_code: str, error_description: str, fast_mode: bool = False) -> bool:
        """
        Orchestrates the recovery loop for failed payments:
        Diagnose -> Select Policy -> Guardrail -> Scheduler.
        """
        logger.info(f"RecoveryService: Initiating recovery pipeline for Transaction {transaction_id} (Reason: {error_code})")
        try:
            db = await get_db()
            txn_doc = await db["transactions"].find_one({"_id": transaction_id})
            if not txn_doc:
                logger.error(f"RecoveryService: Transaction {transaction_id} not found.")
                return False
                
            txn_doc["id"] = txn_doc.pop("_id")
            from app.models.transaction import Transaction
            txn = Transaction(**txn_doc)
            
            # Transition to DIAGNOSING if not already there
            if txn.status != "DIAGNOSING":
                txn.transition_to("DIAGNOSING")
                txn_data = txn.model_dump()
                txn_data["_id"] = txn_data.pop("id")
                await db["transactions"].replace_one({"_id": transaction_id}, txn_data)

            # 1. Run Diagnosis Engine (DIAGNOSING -> DIAGNOSED)
            diag = await diagnosis_engine.diagnose_transaction(transaction_id, error_code=error_code)
            
            # 2. Run Policy Engine (DIAGNOSED -> ACTION_PROPOSED -> GUARDRAIL_CHECK)
            action = await policy_engine.evaluate_policy(transaction_id, diag["root_cause"])
            
            # 3. Run Guardrail Engine (GUARDRAIL_CHECK -> APPROVED / BLOCKED)
            decision = await guardrail_engine.verify_action(action["id"], skip_cooldown_for_test=fast_mode)
            
            if decision["allowed"]:
                # 4. Trigger Retry Scheduler or Notification
                if action["action_type"] == "RETRY_PAYMENT":
                    await retry_scheduler.schedule_retry(action["id"], fast_mode=fast_mode)
                else:
                    # NUDGE_CUSTOMER fallback
                    await self._execute_simulated_customer_nudge(transaction_id, action["id"])
            return True
            
        except Exception as e:
            logger.error(f"RecoveryService: Pipeline execution failed for Transaction {transaction_id}: {e}", exc_info=True)
            return False
            
    async def process_checkout_abandonment(self, transaction_id: str, fast_mode: bool = False) -> bool:
        """
        Orchestrates the recovery loop for abandoned checkouts:
        Diagnose (LLM) -> Select Policy -> Guardrail -> Nudge.
        """
        logger.info(f"RecoveryService: Initiating abandonment recovery pipeline for Transaction {transaction_id}")
        try:
            db = await get_db()
            txn_doc = await db["transactions"].find_one({"_id": transaction_id})
            if not txn_doc:
                logger.error(f"RecoveryService: Transaction {transaction_id} not found.")
                return False
                
            txn_doc["id"] = txn_doc.pop("_id")
            from app.models.transaction import Transaction
            txn = Transaction(**txn_doc)
            
            # Transition to DIAGNOSING if not already there
            if txn.status != "DIAGNOSING":
                txn.transition_to("DIAGNOSING")
                txn_data = txn.model_dump()
                txn_data["_id"] = txn_data.pop("id")
                await db["transactions"].replace_one({"_id": transaction_id}, txn_data)

            # 1. Run Diagnosis Engine (DIAGNOSING -> DIAGNOSED)
            diag = await diagnosis_engine.diagnose_transaction(transaction_id, error_code=None)
            
            # 2. Run Policy Engine (DIAGNOSED -> ACTION_PROPOSED -> GUARDRAIL_CHECK)
            action = await policy_engine.evaluate_policy(transaction_id, diag["root_cause"])
            
            # 3. Run Guardrail Engine (GUARDRAIL_CHECK -> APPROVED / BLOCKED)
            decision = await guardrail_engine.verify_action(action["id"], skip_cooldown_for_test=fast_mode)
            
            if decision["allowed"]:
                # 4. Execute Simulated Nudge
                await self._execute_simulated_customer_nudge(transaction_id, action["id"])
            return True
            
        except Exception as e:
            logger.error(f"RecoveryService: Abandonment pipeline execution failed for Transaction {transaction_id}: {e}", exc_info=True)
            return False

    async def _execute_simulated_customer_nudge(self, transaction_id: str, action_id: str):
        """Simulates customer receiving a nudge notification, clicking it, and successfully paying."""
        db = await get_db()
        
        # Transition recovery action status: -> SUCCESS (simulating message delivery)
        await db["recovery_actions"].update_one(
            {"_id": action_id},
            {"$set": {"status": "SUCCESS", "executed_at": datetime.now(timezone.utc)}}
        )
        
        # Load transaction
        txn_doc = await db["transactions"].find_one({"_id": transaction_id})
        txn_doc["id"] = txn_doc.pop("_id")
        from app.models.transaction import Transaction
        txn = Transaction(**txn_doc)
        
        # Transition transaction state: APPROVED -> EXECUTED -> RECOVERED
        # (For SMS/WhatsApp we assume successful recovery completion inside the simulation)
        txn.transition_to("EXECUTED")
        txn.transition_to("RECOVERED")
        
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": transaction_id}, txn_data)
        
        # Save recovery outcome document
        outcome_doc = {
            "_id": f"out_{uuid_4_hex()}",
            "transaction_id": transaction_id,
            "recovered": True,
            "recovery_method": "NUDGE",
            "recovered_at": datetime.now(timezone.utc),
            "amount_recovered": txn.amount,
            "total_cost": 0.05  # simulated cost (INR)
        }
        await db["recovery_outcomes"].insert_one(outcome_doc)
        
        await log_audit_event(
            transaction_id=transaction_id,
            event_type="PAYMENT_RECOVERED",
            actor="CUSTOMER",
            source="RecoveryService",
            reason="Customer clicked the simulated nudge link and completed authorization.",
            metadata={"action_id": action_id}
        )

def uuid_4_hex() -> str:
    import uuid
    return uuid.uuid4().hex[:8]

recovery_service = RecoveryService()
