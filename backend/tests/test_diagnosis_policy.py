import pytest
import asyncio
from httpx import AsyncClient
from tests.conftest import get_admin_headers
from app.main import app
from app.models.transaction import Transaction
from app.engines.diagnosis.engine import diagnosis_engine
from app.engines.policy.engine import policy_engine

@pytest.mark.asyncio
async def test_deterministic_gateway_diagnosis_and_policy(db):
    """Verify rules classification and policy selection for structured failures."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        # Create a new Checkout session
        checkout_payload = {
            "customer": {
                "name": "Jane Tester",
                "email": "jane@example.com",
                "phone": "+919000000000"
            },
            "cart_value": 1200.00,
            "items": []
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        txn_id = res_chk.json()["transaction_id"]
        
        # Manually shift state to DIAGNOSING for direct testing of the engines
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        txn_doc["id"] = txn_doc.pop("_id")
        txn = Transaction(**txn_doc)
        txn.transition_to("PAYMENT_ATTEMPTED")
        txn.transition_to("DIAGNOSING")
        txn_data = txn.model_dump()
        txn_data["_id"] = txn_data.pop("id")
        await db["transactions"].replace_one({"_id": txn_id}, txn_data)
        
        # 1. Run Diagnosis Engine directly with GATEWAY_TIMEOUT
        diag = await diagnosis_engine.diagnose_transaction(txn_id, error_code="GATEWAY_TIMEOUT")
        assert diag["root_cause"] == "GATEWAY_TIMEOUT"
        assert diag["confidence"] == 1.0
        assert diag["source"] == "RULE_ENGINE"
        
        # Verify transaction status transitioned to DIAGNOSED
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "DIAGNOSED"
        
        # 2. Run Policy Engine directly
        action = await policy_engine.evaluate_policy(txn_id, diag["root_cause"])
        assert action["action_type"] == "RETRY_PAYMENT"
        assert action["channel"] == "API_RETRY"
        assert action["status"] == "PENDING"
        
        # Verify transaction status transitioned to GUARDRAIL_CHECK
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "GUARDRAIL_CHECK"

@pytest.mark.asyncio
async def test_cart_abandonment_llm_fallback_flow(db):
    """Verify that cart abandonments fallback gracefully to UNKNOWN_ABANDONMENT and select appropriate policy."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {
                "name": "Larry Abandon",
                "email": "larry@example.com",
                "phone": "+918888888888"
            },
            "cart_value": 5000.00,
            "items": [],
            "simulated_outcomes": ["SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        chk_id = res_chk.json()["checkout_id"]
        txn_id = res_chk.json()["transaction_id"]
        
        # Abandon checkout session (triggers diagnosis + policy mapping in checkouts.py)
        abandon_payload = {
            "checkout_duration_seconds": 300.0,
            "last_viewed_step": "shipping",
            "selected_payment_method": None
        }
        res_ab = await ac.post(f"/api/v1/checkouts/{chk_id}/abandon", json=abandon_payload)
        assert res_ab.status_code == 200
        
        # Wait for all background tasks to complete before assertions
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()

        # Verify diagnosis record exists in MongoDB and matches the fallback
        diag_doc = await db["diagnoses"].find_one({"transaction_id": txn_id})
        assert diag_doc is not None
        assert diag_doc["source"] == "LLM_FALLBACK"
        assert diag_doc["root_cause"] == "UNKNOWN_ABANDONMENT"
        
        # Verify recovery action document is proposed matching UNKNOWN_ABANDONMENT policy
        action_doc = await db["recovery_actions"].find_one({"transaction_id": txn_id})
        assert action_doc is not None
        assert action_doc["action_type"] == "NUDGE_CUSTOMER"
        assert action_doc["channel"] == "SMS"
        assert action_doc["status"] in ["PENDING", "APPROVED", "SUCCESS"]
        
        # Verify transaction status updated to RECOVERED (auto nudge recovery complete)
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"
