import pytest
import asyncio
from httpx import AsyncClient
from tests.conftest import get_admin_headers
from app.main import app

@pytest.mark.asyncio
async def test_checkout_and_simulated_payment_failure_flow(db):
    """Test full flow: Checkout creation -> Payment attempt fail -> Webhook processing."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        # 1. Create Checkout
        checkout_payload = {
            "customer": {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "phone": "+919876543210"
            },
            "cart_value": 2999.00,
            "items": [
                {
                    "sku": "SKU-1",
                    "name": "Recovr Premium",
                    "price": 2999.0,
                    "quantity": 1
                }
            ],
            "device_info": {
                "platform": "Mobile"
            },
            "simulated_outcomes": ["GATEWAY_TIMEOUT", "SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        assert res_chk.status_code == 201
        chk_data = res_chk.json()
        assert chk_data["success"] is True
        txn_id = chk_data["transaction_id"]
        chk_id = chk_data["checkout_id"]
        
        # Verify transaction state in MongoDB
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "CHECKOUT_INITIATED"

        # 2. Create Payment Intent
        payment_payload = {
            "transaction_id": txn_id,
            "payment_method": "upi",
            "upi_provider": "gpay"
        }
        res_pay = await ac.post("/api/v1/payments/create", json=payment_payload)
        assert res_pay.status_code == 201
        pay_data = res_pay.json()
        assert pay_data["success"] is True
        payment_id = pay_data["payment_id"]

        # Verify transaction status shifted to PAYMENT_ATTEMPTED
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "PAYMENT_ATTEMPTED"

        # 3. Attempt Payment with forced GATEWAY_TIMEOUT failure
        attempt_payload = {
            "payment_id": payment_id,
            "simulated_outcome": "GATEWAY_TIMEOUT"
        }
        res_att = await ac.post("/api/v1/payments/attempt", json=attempt_payload)
        assert res_att.status_code == 200
        att_data = res_att.json()
        assert att_data["success"] is False
        assert att_data["error"]["reason"] == "gateway_timeout"

        # Wait for all background tasks to complete before assertions
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()

        # Verify state is now RECOVERED (auto-retry completed)
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"

        # Verify diagnosis and recovery actions are created in MongoDB
        diag_doc = await db["diagnoses"].find_one({"transaction_id": txn_id})
        assert diag_doc is not None
        assert diag_doc["root_cause"] == "GATEWAY_TIMEOUT"

        action_doc = await db["recovery_actions"].find_one({"transaction_id": txn_id})
        assert action_doc is not None
        assert action_doc["action_type"] == "RETRY_PAYMENT"

        # Verify payment attempts count: 1 failed, 1 success (retry)
        attempts_count = await db["payment_attempts"].count_documents({"transaction_id": txn_id})
        assert attempts_count == 2

        # Verify audit logs
        failed_audit = await db["audit_events"].find_one({"transaction_id": txn_id, "event_type": "PAYMENT_FAILED"})
        assert failed_audit is not None
        assert failed_audit["metadata"]["error_code"] == "GATEWAY_TIMEOUT"

@pytest.mark.asyncio
async def test_manual_checkout_abandonment(db):
    """Test that abandoning a checkout shifts state to CHECKOUT_ABANDONED -> DIAGNOSING -> GUARDRAIL_CHECK."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        # 1. Create Checkout
        checkout_payload = {
            "customer": {
                "name": "Alice Tester",
                "email": "alice@example.com",
                "phone": "+919999900000"
            },
            "cart_value": 2999.00,
            "items": [
                {
                    "sku": "SKU-1",
                    "name": "Test Item",
                    "price": 2999.0,
                    "quantity": 1
                }
            ],
            "simulated_outcomes": ["SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        assert res_chk.status_code == 201
        chk_data = res_chk.json()
        chk_id = chk_data["checkout_id"]
        txn_id = chk_data["transaction_id"]

        # 2. Abandon Checkout
        abandon_payload = {
            "checkout_duration_seconds": 120.5,
            "last_viewed_step": "payment_selection",
            "selected_payment_method": "upi"
        }
        res_ab = await ac.post(f"/api/v1/checkouts/{chk_id}/abandon", json=abandon_payload)
        assert res_ab.status_code == 200
        ab_data = res_ab.json()
        assert ab_data["success"] is True
        
        # Wait for all background tasks to complete before assertions
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()

        # Verify transaction status updated to RECOVERED (customer clicked nudge link and paid)
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"

        # Verify checkout status updated to CHECKOUT_ABANDONED
        chk_doc = await db["checkouts"].find_one({"_id": chk_id})
        assert chk_doc["status"] == "CHECKOUT_ABANDONED"
        assert chk_doc["checkout_duration_seconds"] == 120.5

        # Verify diagnosis and recovery actions are created in MongoDB
        diag_doc = await db["diagnoses"].find_one({"transaction_id": txn_id})
        assert diag_doc is not None
        assert diag_doc["source"] == "LLM_FALLBACK"

        action_doc = await db["recovery_actions"].find_one({"transaction_id": txn_id})
        assert action_doc is not None
        assert action_doc["action_type"] == "NUDGE_CUSTOMER"

        # Verify audit event logged
        abandon_audit = await db["audit_events"].find_one({"transaction_id": txn_id, "event_type": "CHECKOUT_ABANDONED"})
        assert abandon_audit is not None
        assert abandon_audit["metadata"]["checkout_duration_seconds"] == 120.5
