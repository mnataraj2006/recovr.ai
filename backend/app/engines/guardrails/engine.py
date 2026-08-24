import uuid
import logging
from datetime import datetime, timezone
from app.db.connection import get_db
from app.models.transaction import Transaction
from app.audit.logger import log_audit_event

logger = logging.getLogger(__name__)

# Cooldown default in seconds (5 minutes)
COOLDOWN_SECONDS = 300

class GuardrailEngine:
    async def verify_action(self, action_id: str, skip_cooldown_for_test: bool = False) -> dict:
        """
        Executes safety, compliance, and duplication guardrails on a proposed action.
        Transitions the Transaction status based on the guardrail outcome.
        """
        db = await get_db()
        
        # 1. Fetch Recovery Action
        action_doc = await db["recovery_actions"].find_one({"_id": action_id})
        if not action_doc:
            raise ValueError(f"Recovery action {action_id} not found.")
            
        txn_id = action_doc["transaction_id"]
        action_type = action_doc["action_type"]
        channel = action_doc["channel"]
        
        # 2. Fetch Transaction
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        if not txn_doc:
            raise ValueError(f"Transaction {txn_id} not found.")
            
        txn_doc["id"] = txn_doc.pop("_id")
        txn = Transaction(**txn_doc)
        
        # 3. Fetch Diagnosis to check limits per cause
        diag_doc = await db["diagnoses"].find_one({"transaction_id": txn_id})
        root_cause = diag_doc["root_cause"] if diag_doc else "UNKNOWN_ABANDONMENT"
        
        checks = []
        allowed = True
        block_reason = "All recovery guardrails passed."
        
        # --- Check 1: Transaction Status Check ---
        status_ok = txn.status == "GUARDRAIL_CHECK"
        checks.append({"name": "transaction_status", "passed": status_ok})
        if not status_ok:
            allowed = False
            block_reason = f"Transaction is in state {txn.status}, not eligible for guardrail checks."

        # --- Check 2: Already Paid Check (Double charge protection) ---
        if allowed:
            # Check if any payment attempt succeeded for this transaction
            success_attempts = await db["payment_attempts"].count_documents({
                "transaction_id": txn_id,
                "status": "Success"
            })
            # Also check if another transaction for the same checkout has succeeded
            success_txn = await db["transactions"].count_documents({
                "checkout_id": txn.checkout_id,
                "status": {"$in": ["SUCCESS", "RECOVERED"]}
            })
            paid_ok = (success_attempts == 0) and (success_txn == 0)
            checks.append({"name": "duplicate_payment_protection", "passed": paid_ok})
            if not paid_ok:
                allowed = False
                block_reason = "Checkout already has a successful payment. Action blocked to prevent double charge."

        # --- Check 3: Retry Limit Check ---
        if allowed and action_type == "RETRY_PAYMENT":
            failed_attempts = await db["payment_attempts"].count_documents({
                "transaction_id": txn_id,
                "status": "Failed"
            })
            print(f"GUARDRAIL CHECK FOR {txn_id}: FAILED ATTEMPTS COUNT = {failed_attempts}")
            retry_ok = failed_attempts < 3
            checks.append({"name": "retry_limit", "passed": retry_ok})
            if not retry_ok:
                allowed = False
                block_reason = f"Payment retry cap (3 total attempts) exceeded. Current failed attempts: {failed_attempts}."

        # --- Check 4: Nudge Limit Check ---
        if allowed and action_type == "NUDGE_CUSTOMER":
            sent_nudges = await db["recovery_actions"].count_documents({
                "transaction_id": txn_id,
                "action_type": "NUDGE_CUSTOMER",
                "status": "SUCCESS"
            })
            # Price hesitation allows 2 nudges, others allow 1
            max_nudges = 2 if root_cause == "PRICE_HESITATION" else 1
            nudge_ok = sent_nudges < max_nudges
            checks.append({"name": "nudge_limit", "passed": nudge_ok})
            if not nudge_ok:
                allowed = False
                block_reason = f"Customer nudge cap ({max_nudges} nudges) exceeded for cause {root_cause}."

        # --- Check 5: Cooldown Check ---
        if allowed and action_type == "NUDGE_CUSTOMER" and not skip_cooldown_for_test:
            # Fetch last successful nudge
            last_nudge = await db["recovery_actions"].find_one(
                {
                    "transaction_id": txn_id,
                    "action_type": "NUDGE_CUSTOMER",
                    "status": "SUCCESS"
                },
                sort=[("created_at", -1)]
            )
            cooldown_ok = True
            if last_nudge:
                elapsed = (datetime.now(timezone.utc) - last_nudge["created_at"].replace(tzinfo=timezone.utc)).total_seconds()
                cooldown_ok = elapsed >= COOLDOWN_SECONDS
            checks.append({"name": "cooldown_period", "passed": cooldown_ok})
            if not cooldown_ok:
                allowed = False
                block_reason = f"Action blocked due to active cooldown. Nudge was sent {elapsed:.1f}s ago (min wait: {COOLDOWN_SECONDS}s)."

        # --- Check 6: Incentive Limit Check ---
        if allowed:
            # Check if any discounts exceed 10% or ₹500
            incentive = action_doc.get("payload", {}).get("incentive", {})
            incentive_value = incentive.get("value", 0.0)
            
            incentive_ok = True
            if incentive_value > 0.0:
                pct_cap = txn.amount * 0.10
                abs_cap = 500.0
                if incentive_value > pct_cap or incentive_value > abs_cap:
                    incentive_ok = False
            
            checks.append({"name": "incentive_limit", "passed": incentive_ok})
            if not incentive_ok:
                allowed = False
                block_reason = f"Proposed discount coupon (₹{incentive_value}) exceeds allowed threshold (10% cart or max ₹500)."

        # --- Check 7: Action Validity ---
        if allowed:
            valid_action = action_type in ["RETRY_PAYMENT", "NUDGE_CUSTOMER"]
            checks.append({"name": "action_validity", "passed": valid_action})
            if not valid_action:
                allowed = False
                block_reason = f"Action type '{action_type}' is invalid."

        decision_id = f"gdl_{uuid.uuid4().hex[:8]}"
        
        # 4. Save Guardrail Decision Document
        decision_doc = {
            "_id": decision_id,
            "transaction_id": txn_id,
            "action_id": action_id,
            "allowed": allowed,
            "checks_run": checks,
            "reason": block_reason,
            "created_at": datetime.now(timezone.utc)
        }
        await db["guardrail_decisions"].insert_one(decision_doc)
        
        await log_audit_event(
            transaction_id=txn_id,
            event_type="GUARDRAIL_CHECKED",
            actor="SYSTEM",
            source="GuardrailEngine",
            reason=f"Guardrail evaluation completed. Allowed: {allowed}. Reason: {block_reason}",
            metadata={"action_id": action_id, "allowed": allowed}
        )
        
        # 5. Transition transaction state
        if allowed:
            # Approved -> Change state to APPROVED
            txn.transition_to("APPROVED")
            await db["recovery_actions"].update_one(
                {"_id": action_id},
                {"$set": {"status": "APPROVED"}}
            )
            await log_audit_event(
                transaction_id=txn_id,
                event_type="RECOVERY_ACTION_APPROVED",
                actor="SYSTEM",
                source="GuardrailEngine",
                reason=f"Recovery action approved: {action_type} via {channel}.",
                metadata={"action_id": action_id, "decision_id": decision_id}
            )
        else:
            # Blocked -> Change state to UNRECOVERABLE if not already terminal
            if txn.status not in ["RECOVERED", "SUCCESS"]:
                txn.transition_to("BLOCKED")
                txn.transition_to("UNRECOVERABLE")
            
            await db["recovery_actions"].update_one(
                {"_id": action_id},
                {"$set": {"status": "BLOCKED"}}
            )
            await log_audit_event(
                transaction_id=txn_id,
                event_type="RECOVERY_ACTION_BLOCKED",
                actor="SYSTEM",
                source="GuardrailEngine",
                reason=f"Recovery action blocked: {block_reason}",
                metadata={"action_id": action_id, "decision_id": decision_id, "reason": block_reason}
            )
            
        # Save transaction status update
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": txn_id}, txn_data)
        
        return {
            "allowed": allowed,
            "reason": block_reason,
            "checks": checks
        }

guardrail_engine = GuardrailEngine()
