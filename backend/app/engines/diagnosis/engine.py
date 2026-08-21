import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from app.db.connection import get_db
from app.models.transaction import Transaction
from app.ai.diagnosis import diagnose_checkout_abandonment
from app.audit.logger import log_audit_event

logger = logging.getLogger(__name__)

# Deterministic lookup table for gateway codes to root cause categories
GATEWAY_RULES = {
    "INSUFFICIENT_FUNDS": {
        "root_cause": "INSUFFICIENT_FUNDS",
        "reasoning": "Gateway reported card/account balance deficit.",
        "rule_triggered": "GATEWAY_RULE_INSUFFICIENT_FUNDS"
    },
    "GATEWAY_TIMEOUT": {
        "root_cause": "GATEWAY_TIMEOUT",
        "reasoning": "Gateway reported connection timed out before bank response received.",
        "rule_triggered": "GATEWAY_RULE_TIMEOUT"
    },
    "OTP_FAILURE": {
        "root_cause": "OTP_FAILURE",
        "reasoning": "User failed to enter correct OTP token before validation session closed.",
        "rule_triggered": "GATEWAY_RULE_OTP"
    },
    "NETWORK_ERROR": {
        "root_cause": "NETWORK_ERROR",
        "reasoning": "A raw network connection loss occurred.",
        "rule_triggered": "GATEWAY_RULE_NETWORK"
    },
    "PAYMENT_CANCELLED": {
        "root_cause": "PAYMENT_CANCELLED",
        "reasoning": "User manually declined or pressed back button on gateway interface.",
        "rule_triggered": "GATEWAY_RULE_CANCELLED"
    }
}

class DiagnosisEngine:
    async def diagnose_transaction(self, transaction_id: str, error_code: Optional[str] = None) -> dict:
        """
        Diagnoses the root cause of a failed or abandoned transaction.
        Checks deterministic rules first, then falls back to Claude.
        """
        db = await get_db()
        
        # 1. Fetch transaction
        txn_doc = await db["transactions"].find_one({"_id": transaction_id})
        if not txn_doc:
            raise ValueError(f"Transaction {transaction_id} not found.")
            
        txn_doc["id"] = txn_doc.pop("_id")
        txn = Transaction(**txn_doc)
        
        # Verify transaction status is in DIAGNOSING
        if txn.status != "DIAGNOSING":
            raise ValueError(f"Transaction {transaction_id} is in status {txn.status}, not DIAGNOSING.")
            
        # Fetch linked checkout session
        checkout_doc = await db["checkouts"].find_one({"_id": txn.checkout_id})
        
        diagnosis_id = f"diag_{uuid.uuid4().hex[:8]}"
        root_cause = "UNKNOWN_ABANDONMENT"
        confidence = 0.5
        source = "RULE_ENGINE"
        rule_triggered = None
        reasoning = "Could not diagnose failure cause via rules or behavioral metrics."
        
        # Path A: Check deterministic rules
        if error_code and error_code.upper() in GATEWAY_RULES:
            rule_detail = GATEWAY_RULES[error_code.upper()]
            root_cause = rule_detail["root_cause"]
            confidence = 1.0
            source = "RULE_ENGINE"
            rule_triggered = rule_detail["rule_triggered"]
            reasoning = rule_detail["reasoning"]
            logger.info(f"DiagnosisEngine: Classified {transaction_id} as {root_cause} via rule: {rule_triggered}")
            
        # Path B: Fallback to LLM analysis for Cart Abandons
        else:
            source = "LLM_FALLBACK"
            telemetry = {
                "cart_value": txn.amount,
                "checkout_duration_seconds": checkout_doc.get("checkout_duration_seconds", 0.0) if checkout_doc else 0.0,
                "device_info": checkout_doc.get("device_info", {}) if checkout_doc else {},
                "checkout_status": checkout_doc.get("status", "") if checkout_doc else ""
            }
            
            # Add historical details if customer has multiple checkout events
            prev_checkouts_count = await db["checkouts"].count_documents({"customer_id": txn.customer_id})
            telemetry["customer_previous_checkouts_count"] = prev_checkouts_count
            
            llm_res = await diagnose_checkout_abandonment(telemetry)
            root_cause = llm_res.cause
            confidence = llm_res.confidence
            reasoning = llm_res.reason
            rule_triggered = None
            logger.info(f"DiagnosisEngine: Classified {transaction_id} as {root_cause} via Claude Fallback.")
            
        # 3. Create Diagnosis document
        diagnosis_doc = {
            "_id": diagnosis_id,
            "transaction_id": transaction_id,
            "root_cause": root_cause,
            "confidence": confidence,
            "source": source,
            "rule_triggered": rule_triggered,
            "reasoning": reasoning,
            "created_at": datetime.now(timezone.utc)
        }
        await db["diagnoses"].insert_one(diagnosis_doc)
        
        # 4. Transition transaction status: -> DIAGNOSED
        txn.transition_to("DIAGNOSED")
        txn.root_cause_id = diagnosis_id
        
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": transaction_id}, txn_data)
        
        # 5. Log audit event
        await log_audit_event(
            transaction_id=transaction_id,
            event_type="DIAGNOSIS_CREATED",
            actor="AGENT",
            source="DiagnosisEngine",
            reason=f"Diagnosed cause as {root_cause} (Source: {source}, Confidence: {confidence})",
            metadata={
                "root_cause": root_cause,
                "source": source,
                "confidence": confidence,
                "reasoning": reasoning
            }
        )
        
        # Convert _id back to id for return object
        diagnosis_doc["id"] = diagnosis_doc.pop("_id")
        return diagnosis_doc

diagnosis_engine = DiagnosisEngine()
