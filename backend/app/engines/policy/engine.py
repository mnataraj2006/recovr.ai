import uuid
import logging
from datetime import datetime, timezone
from app.db.connection import get_db
from app.models.transaction import Transaction
from app.audit.logger import log_audit_event

logger = logging.getLogger(__name__)

# Configurable recovery policy table mapping cause -> (action, channel, explanation)
POLICY_TABLE = {
    "GATEWAY_TIMEOUT": {
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "reasoning": "Gateway timeout is considered a transient connection drop. Background retry is appropriate."
    },
    "NETWORK_ERROR": {
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "reasoning": "Network packet loss is temporary. Background auto-retry minimizes checkout abandonment."
    },
    "INSUFFICIENT_FUNDS": {
        "action_type": "NUDGE_CUSTOMER",
        "channel": "WHATSAPP",
        "reasoning": "The customer's account has insufficient balance. WhatsApp notification with alternate payment method suggested."
    },
    "OTP_FAILURE": {
        "action_type": "NUDGE_CUSTOMER",
        "channel": "SMS",
        "reasoning": "OTP entry timeouts represent user interface friction. direct link to re-authorize payment sent via SMS."
    },
    "PAYMENT_CANCELLED": {
        "action_type": "NUDGE_CUSTOMER",
        "channel": "SMS",
        "reasoning": "User manually cancelled transaction. Nudge customer with soft reminder to recover cart."
    },
    "PRICE_HESITATION": {
        "action_type": "NUDGE_CUSTOMER",
        "channel": "EMAIL",
        "reasoning": "Customer spent long time hesitating on cart cost. Send discount coupon nudge."
    },
    "UX_FRUSTRATION": {
        "action_type": "NUDGE_CUSTOMER",
        "channel": "WHATSAPP",
        "reasoning": "Repeated interface lag or form errors occurred. WhatsApp direct payment link sent to bypass gateway."
    },
    "UNKNOWN_ABANDONMENT": {
        "action_type": "NUDGE_CUSTOMER",
        "channel": "SMS",
        "reasoning": "Checkout was abandoned without specific gateway errors. Send gentle recovery link reminder."
    }
}

class PolicyEngine:
    async def evaluate_policy(self, transaction_id: str, root_cause: str) -> dict:
        """
        Determines the optimal recovery action based on the diagnosed root cause.
        Transitions the Transaction to ACTION_PROPOSED -> GUARDRAIL_CHECK status.
        """
        db = await get_db()
        
        # 1. Fetch transaction
        txn_doc = await db["transactions"].find_one({"_id": transaction_id})
        if not txn_doc:
            raise ValueError(f"Transaction {transaction_id} not found.")
            
        txn_doc["id"] = txn_doc.pop("_id")
        txn = Transaction(**txn_doc)
        
        # Verify transaction status is DIAGNOSED
        if txn.status != "DIAGNOSED":
            raise ValueError(f"Transaction {transaction_id} is in status {txn.status}, not DIAGNOSED.")

        # 2. Lookup policy mappings
        cause_upper = root_cause.upper()
        policy = POLICY_TABLE.get(cause_upper, POLICY_TABLE["UNKNOWN_ABANDONMENT"])
        
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        
        # 3. Create proposed recovery action document
        action_doc = {
            "_id": action_id,
            "transaction_id": transaction_id,
            "action_type": policy["action_type"],
            "channel": policy["channel"],
            "scheduled_for": datetime.now(timezone.utc),
            "status": "PENDING",
            "payload": {
                "reasoning": policy["reasoning"]
            },
            "created_at": datetime.now(timezone.utc)
        }
        await db["recovery_actions"].insert_one(action_doc)
        
        # 4. Transition transaction state: -> ACTION_PROPOSED -> GUARDRAIL_CHECK
        txn.transition_to("ACTION_PROPOSED")
        txn.transition_to("GUARDRAIL_CHECK")
        
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": transaction_id}, txn_data)
        
        # 5. Log audit event
        await log_audit_event(
            transaction_id=transaction_id,
            event_type="POLICY_SELECTED",
            actor="AGENT",
            source="PolicyEngine",
            reason=f"Selected recovery action: {policy['action_type']} via {policy['channel']}",
            metadata={
                "action_id": action_id,
                "action_type": policy["action_type"],
                "channel": policy["channel"],
                "policy_reasoning": policy["reasoning"]
            }
        )
        
        action_doc["id"] = action_doc.pop("_id")
        return action_doc

policy_engine = PolicyEngine()
