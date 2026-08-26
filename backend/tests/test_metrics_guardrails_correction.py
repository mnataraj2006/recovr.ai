import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from tests.conftest import get_admin_headers
from app.main import app
from app.engines.guardrails.engine import guardrail_engine

@pytest.mark.asyncio
async def test_deterministic_metrics_dataset_verification(db):
    """
    SECTION 17 & 21 ACCEPTANCE TEST:
    Verifies metrics accuracy against a deterministic dataset of 5 transactions.
    """
    # 1. Clear any existing collections in this function's test database
    await db["transactions"].delete_many({})
    await db["payment_attempts"].delete_many({})
    await db["recovery_actions"].delete_many({})
    await db["diagnoses"].delete_many({})
    
    # Txn 1: ₹1000 Initial SUCCESS (Normal success, never at risk)
    txn_1_id = f"txn_det_1_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_1_id,
        "checkout_id": "chk_1",
        "customer_id": "cust_1",
        "amount": 1000.0,
        "status": "SUCCESS"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_1_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_1_id,
        "attempt_number": 1,
        "status": "Success"
    })
    
    # Txn 2: ₹2000 FAILED -> Recovery SUCCESS (At-risk & RECOVERED)
    txn_2_id = f"txn_det_2_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_2_id,
        "checkout_id": "chk_2",
        "customer_id": "cust_2",
        "amount": 2000.0,
        "status": "RECOVERED"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_2_1_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_2_id,
        "attempt_number": 1,
        "status": "Failed",
        "gateway_error_code": "GATEWAY_TIMEOUT"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_2_2_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_2_id,
        "attempt_number": 2,
        "status": "Success"
    })
    await db["recovery_actions"].insert_one({
        "_id": f"act_2_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_2_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "SUCCESS"
    })
    
    # Txn 3: ₹3000 FAILED -> Recovery FAILED (At-risk, unrecovered)
    txn_3_id = f"txn_det_3_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_3_id,
        "checkout_id": "chk_3",
        "customer_id": "cust_3",
        "amount": 3000.0,
        "status": "RETRY_ESCALATE"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_3_1_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_3_id,
        "attempt_number": 1,
        "status": "Failed",
        "gateway_error_code": "GATEWAY_TIMEOUT"
    })
    
    # Txn 4: ₹4000 ABANDONED -> Nudge -> No return (At-risk, unrecovered)
    txn_4_id = f"txn_det_4_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_4_id,
        "checkout_id": "chk_4",
        "customer_id": "cust_4",
        "amount": 4000.0,
        "status": "CHECKOUT_ABANDONED"
    })
    
    # Txn 5: ₹5000 FAILED -> Retry limit exceeded (At-risk, UNRECOVERABLE)
    txn_5_id = f"txn_det_5_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_5_id,
        "checkout_id": "chk_5",
        "customer_id": "cust_5",
        "amount": 5000.0,
        "status": "UNRECOVERABLE"
    })
    for i in range(3):
        await db["payment_attempts"].insert_one({
            "_id": f"att_5_{i+1}_{uuid.uuid4().hex[:6]}",
            "transaction_id": txn_5_id,
            "attempt_number": i + 1,
            "status": "Failed",
            "gateway_error_code": "GATEWAY_TIMEOUT"
        })

    # Fetch Metrics via API
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        res = await ac.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        
        # Invariants Check
        assert data["total_transactions"] == 5
        assert data["at_risk_transactions"] == 4
        assert data["recovered_transactions"] == 1
        assert abs(data["transaction_recovery_rate"] - 0.25) < 0.0001
        assert data["total_transaction_value"] == 15000.0
        assert data["revenue_at_risk"] == 14000.0
        assert data["recovered_revenue"] == 2000.0
        assert abs(data["revenue_recovery_rate"] - (2000.0 / 14000.0)) < 0.0001
        
        # Verify normal initial success (₹1000) is NOT included in recovered revenue
        assert data["recovered_revenue"] != 3000.0

@pytest.mark.asyncio
async def test_guardrail_cooldown_non_terminal_block(db):
    """TEST A: Cooldown block -> terminal=False, transaction remains active."""
    txn_id = f"txn_cd_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_cd",
        "customer_id": "cust_cd",
        "amount": 1000.0,
        "status": "GUARDRAIL_CHECK"
    })
    await db["diagnoses"].insert_one({
        "transaction_id": txn_id,
        "root_cause": "PRICE_HESITATION"
    })
    # Last nudge sent just 10 seconds ago
    await db["recovery_actions"].insert_one({
        "_id": f"act_cd_1_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_id,
        "action_type": "NUDGE_CUSTOMER",
        "channel": "EMAIL",
        "status": "SUCCESS",
        "created_at": datetime.now(timezone.utc)
    })
    action_2_id = f"act_cd_2_{uuid.uuid4().hex[:6]}"
    await db["recovery_actions"].insert_one({
        "_id": action_2_id,
        "transaction_id": txn_id,
        "action_type": "NUDGE_CUSTOMER",
        "channel": "EMAIL",
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc)
    })
    
    res = await guardrail_engine.verify_action(action_2_id, skip_cooldown_for_test=False)
    assert res["allowed"] is False
    assert "cooldown" in res["reason"].lower()
    assert res["terminal"] is False
    
    # Verify transaction was NOT converted to UNRECOVERABLE
    txn_doc = await db["transactions"].find_one({"_id": txn_id})
    assert txn_doc["status"] != "UNRECOVERABLE"

@pytest.mark.asyncio
async def test_guardrail_retry_limit_terminal_block(db):
    """TEST B: Retry Limit block -> terminal=True, transaction becomes UNRECOVERABLE."""
    txn_id = f"txn_rl_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_rl",
        "customer_id": "cust_rl",
        "amount": 1000.0,
        "status": "GUARDRAIL_CHECK"
    })
    for i in range(3):
        await db["payment_attempts"].insert_one({
            "_id": f"att_rl_{i+1}_{uuid.uuid4().hex[:6]}",
            "transaction_id": txn_id,
            "attempt_number": i + 1,
            "status": "Failed"
        })
    action_id = f"act_rl_{uuid.uuid4().hex[:6]}"
    await db["recovery_actions"].insert_one({
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "PENDING"
    })
    
    res = await guardrail_engine.verify_action(action_id)
    assert res["allowed"] is False
    assert "retry cap" in res["reason"].lower()
    assert res["terminal"] is True
    
    # Verify transaction became UNRECOVERABLE
    txn_doc = await db["transactions"].find_one({"_id": txn_id})
    assert txn_doc["status"] == "UNRECOVERABLE"

@pytest.mark.asyncio
async def test_guardrail_already_recovered_non_terminal_block(db):
    """TEST C: Already Recovered block -> terminal=False, transaction remains RECOVERED."""
    txn_id = f"txn_ar_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_ar",
        "customer_id": "cust_ar",
        "amount": 2500.0,
        "status": "GUARDRAIL_CHECK"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_ar_1_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_id,
        "attempt_number": 1,
        "status": "Success"
    })
    action_id = f"act_ar_{uuid.uuid4().hex[:6]}"
    await db["recovery_actions"].insert_one({
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "PENDING"
    })
    
    res = await guardrail_engine.verify_action(action_id)
    assert res["allowed"] is False
    assert "already has a successful payment" in res["reason"].lower()
    assert res["terminal"] is False
    
    # Verify transaction status was NOT altered to UNRECOVERABLE
    txn_doc = await db["transactions"].find_one({"_id": txn_id})
    assert txn_doc["status"] != "UNRECOVERABLE"
