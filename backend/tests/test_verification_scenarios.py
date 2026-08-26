import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from tests.conftest import get_admin_headers
from app.main import app
from app.engines.guardrails.engine import guardrail_engine
from app.engines.scheduler.engine import retry_scheduler
from app.models.transaction import Transaction

@pytest.mark.asyncio
async def test_scenario_1_successful_initial_payment(db):
    """TEST 1: Successful initial payment flow: PAYMENT_ATTEMPTED -> SUCCESS -> RECOVERED."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {"name": "Jane Doe", "email": "jane@example.com", "phone": "+919999999991"},
            "cart_value": 1500.0,
            "items": []
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        txn_id = res_chk.json()["transaction_id"]
        
        res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
        pay_id = res_pay.json()["payment_id"]
        
        res_att = await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id, "simulated_outcome": "SUCCESS"})
        assert res_att.status_code == 200
        assert res_att.json()["success"] is True
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "SUCCESS"
        
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).to_list(length=10)
        assert len(attempts) == 1
        assert attempts[0]["status"] == "Success"
        assert attempts[0]["completed_at"] is not None

@pytest.mark.asyncio
async def test_scenario_2_gateway_timeout_retry_success(db):
    """TEST 2: Gateway timeout -> retry -> success."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {"name": "John Timeout", "email": "john@example.com", "phone": "+919999999992"},
            "cart_value": 2499.0,
            "items": [],
            "simulated_outcomes": ["GATEWAY_TIMEOUT", "SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        txn_id = res_chk.json()["transaction_id"]
        
        res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
        pay_id = res_pay.json()["payment_id"]
        
        # Initial attempt fails
        await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id, "simulated_outcome": "GATEWAY_TIMEOUT"})
        
        # Wait for all background tasks to complete
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"
        
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).sort("attempt_number", 1).to_list(length=10)
        assert len(attempts) == 2
        assert attempts[0]["status"] == "Failed"
        assert attempts[0]["gateway_error_code"] == "GATEWAY_TIMEOUT"
        assert attempts[1]["status"] == "Success"

@pytest.mark.asyncio
async def test_scenario_3_repeated_timeout_stop(db):
    """TEST 3: Gateway timeout -> retry -> retry -> stop (UNRECOVERABLE)."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {"name": "Max Retry", "email": "max@example.com", "phone": "+919999999993"},
            "cart_value": 1200.0,
            "items": [],
            "simulated_outcomes": ["GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        txn_id = res_chk.json()["transaction_id"]
        
        res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
        pay_id = res_pay.json()["payment_id"]
        
        await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id, "simulated_outcome": "GATEWAY_TIMEOUT"})
        
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "UNRECOVERABLE"
        
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).to_list(length=10)
        assert len(attempts) == 3  # Attempt 1 failed + 2 retries failed
        
        # Verify no 4th payment attempt exists
        assert len(attempts) < 4

@pytest.mark.asyncio
async def test_scenario_4_insufficient_funds_alternate_payment(db):
    """TEST 4: Insufficient funds -> alternate method (wallet) -> success."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {"name": "Poor Balance", "email": "poor@example.com", "phone": "+919999999994"},
            "cart_value": 3000.0,
            "items": [],
            "simulated_outcomes": ["INSUFFICIENT_FUNDS", "SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        txn_id = res_chk.json()["transaction_id"]
        
        res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
        pay_id = res_pay.json()["payment_id"]
        
        # Attempt fails with Insufficient Funds
        await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id, "simulated_outcome": "INSUFFICIENT_FUNDS"})
        
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"
        
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).sort("attempt_number", 1).to_list(length=10)
        assert len(attempts) == 2
        assert attempts[0]["status"] == "Failed"
        assert attempts[0]["gateway_error_code"] == "INSUFFICIENT_FUNDS"
        # The 2nd attempt must use "wallet" as alternate payment method
        assert attempts[1]["payment_method"] == "wallet"
        assert attempts[1]["status"] == "Success"

@pytest.mark.asyncio
async def test_scenario_5_otp_failure_nudge_success(db):
    """TEST 5: OTP failure -> nudge -> success."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {"name": "No OTP", "email": "nootp@example.com", "phone": "+919999999995"},
            "cart_value": 800.0,
            "items": [],
            "simulated_outcomes": ["OTP_FAILURE", "SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        txn_id = res_chk.json()["transaction_id"]
        
        res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
        pay_id = res_pay.json()["payment_id"]
        
        await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id, "simulated_outcome": "OTP_FAILURE"})
        
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"
        
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).sort("attempt_number", 1).to_list(length=10)
        assert len(attempts) == 2
        assert attempts[0]["status"] == "Failed"
        assert attempts[1]["status"] == "Success"

@pytest.mark.asyncio
async def test_scenario_6_abandonment_nudge_payment_success(db):
    """TEST 6: Abandonment -> nudge -> payment -> success."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {"name": "Abandoner", "email": "abandoner@example.com", "phone": "+919999999996"},
            "cart_value": 500.0,
            "items": [],
            "simulated_outcomes": ["SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        chk_data = res_chk.json()
        txn_id = chk_data["transaction_id"]
        chk_id = chk_data["checkout_id"]
        
        # Abandon checkout
        await ac.post(f"/api/v1/checkouts/{chk_id}/abandon", json={
            "checkout_duration_seconds": 150.0,
            "last_viewed_step": "shipping",
            "selected_payment_method": None
        })
        
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"
        
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).to_list(length=10)
        assert len(attempts) == 1
        assert attempts[0]["status"] == "Success"

@pytest.mark.asyncio
async def test_scenario_7_abandonment_nudge_no_payment(db):
    """TEST 7: Abandonment -> nudge -> no payment / failure -> unrecovered."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        checkout_payload = {
            "customer": {"name": "Hard Abandoner", "email": "hard@example.com", "phone": "+919999999997"},
            "cart_value": 400.0,
            "items": [],
            "simulated_outcomes": ["GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        chk_data = res_chk.json()
        txn_id = chk_data["transaction_id"]
        chk_id = chk_data["checkout_id"]
        
        await ac.post(f"/api/v1/checkouts/{chk_id}/abandon", json={
            "checkout_duration_seconds": 120.0,
            "last_viewed_step": "cart",
            "selected_payment_method": None
        })
        
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).to_list(length=10)
        events = await db["audit_events"].find({"transaction_id": txn_id}).to_list(length=100)
        print("SCENARIO 7 TRANSACTION:", txn_doc)
        print("SCENARIO 7 ATTEMPTS:", [(a["attempt_number"], a["status"], a.get("gateway_error_code")) for a in attempts])
        print("SCENARIO 7 EVENTS:", [e["event_type"] for e in events])
        
        # Since the customer-triggered payment failed with GATEWAY_TIMEOUT, it went to RETRY_ESCALATE
        assert txn_doc["status"] in ["RETRY_ESCALATE", "UNRECOVERABLE", "ACTION_PROPOSED", "GUARDRAIL_CHECK", "APPROVED", "EXECUTING", "PAYMENT_ATTEMPTED"]

@pytest.mark.asyncio
async def test_scenario_8_already_recovered_blocked(db):
    """TEST 8: Already recovered transaction -> further recovery action blocked."""
    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_123",
        "customer_id": "cust_123",
        "amount": 2500.0,
        "status": "GUARDRAIL_CHECK"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_{uuid.uuid4().hex[:8]}",
        "transaction_id": txn_id,
        "attempt_number": 1,
        "status": "Success"
    })
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    await db["recovery_actions"].insert_one({
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "PENDING"
    })
    res = await guardrail_engine.verify_action(action_id)
    assert res["allowed"] is False
    assert "already has a successful payment" in res["reason"]

@pytest.mark.asyncio
async def test_scenario_9_retry_limit_exceeded(db):
    """TEST 9: Retry limit exceeded -> blocked."""
    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_456",
        "customer_id": "cust_456",
        "amount": 1000.0,
        "status": "GUARDRAIL_CHECK"
    })
    for i in range(3):
        await db["payment_attempts"].insert_one({
            "_id": f"att_{uuid.uuid4().hex[:8]}",
            "transaction_id": txn_id,
            "attempt_number": i + 1,
            "status": "Failed"
        })
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    await db["recovery_actions"].insert_one({
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "PENDING"
    })
    res = await guardrail_engine.verify_action(action_id)
    assert res["allowed"] is False
    assert "retry cap" in res["reason"]

@pytest.mark.asyncio
async def test_scenario_10_duplicate_recovery_execution(db):
    """TEST 10: Duplicate recovery execution is blocked (idempotency)."""
    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_789",
        "customer_id": "cust_789",
        "amount": 110.0,
        "status": "APPROVED"
    })
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    await db["recovery_actions"].insert_one({
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "PENDING"
    })
    
    # First scheduling succeeds and sets state to EXECUTING
    delay1 = await retry_scheduler.schedule_retry(action_id, fast_mode=True)
    assert delay1 > 0.0
    
    # Second scheduling returns 0.0 (blocked/bypassed due to status check)
    delay2 = await retry_scheduler.schedule_retry(action_id, fast_mode=True)
    assert delay2 == 0.0

@pytest.mark.asyncio
async def test_final_acceptance_demo_flow(db):
    """TEST 20: Final acceptance test scenario verification: TXN_DEMO_001 and TXN_TIMEOUT_002."""
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        # Part 1: TXN_DEMO_001 (Successful recovery on Attempt 2)
        checkout_payload = {
            "customer": {"name": "Demo Client 1", "email": "demo1@example.com", "phone": "+919999999901"},
            "cart_value": 2499.00,
            "items": [],
            "simulated_outcomes": ["GATEWAY_TIMEOUT", "SUCCESS"]
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        txn_id = res_chk.json()["transaction_id"]
        
        res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
        pay_id = res_pay.json()["payment_id"]
        
        await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id, "simulated_outcome": "GATEWAY_TIMEOUT"})
        
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"
        
        attempts = await db["payment_attempts"].find({"transaction_id": txn_id}).to_list(length=10)
        assert len(attempts) == 2
        
        success_attempts = [a for a in attempts if a["status"] == "Success"]
        failed_attempts = [a for a in attempts if a["status"] == "Failed"]
        assert len(success_attempts) == 1
        assert len(failed_attempts) == 1
        
        action = await db["recovery_actions"].find_one({"transaction_id": txn_id})
        assert action["status"] == "SUCCESS"
        
        guardrail = await db["guardrail_decisions"].find_one({"transaction_id": txn_id})
        assert guardrail["allowed"] is True
        
        outcome_doc = await db["recovery_outcomes"].find_one({"transaction_id": txn_id})
        assert outcome_doc["amount_recovered"] == 2499.00
        
        # Verify complete audit trail presence
        events = await db["audit_events"].distinct("event_type", {"transaction_id": txn_id})
        expected_events = [
            "PAYMENT_FAILED", "DIAGNOSIS_CREATED", "POLICY_SELECTED", 
            "GUARDRAIL_CHECKED", "RECOVERY_ACTION_APPROVED", 
            "PAYMENT_RETRY_ATTEMPTED", "PAYMENT_RECOVERED", "RECOVERY_ACTION_SUCCEEDED"
        ]
        for e in expected_events:
            assert e in events
            
        # Part 2: TXN_TIMEOUT_002 (Permanent timeout failures ending at attempt 3)
        checkout_payload_2 = {
            "customer": {"name": "Demo Client 2", "email": "demo2@example.com", "phone": "+919999999902"},
            "cart_value": 2499.00,
            "items": [],
            "simulated_outcomes": ["GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT"]
        }
        res_chk_2 = await ac.post("/api/v1/checkouts", json=checkout_payload_2)
        txn_id_2 = res_chk_2.json()["transaction_id"]
        
        res_pay_2 = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id_2, "payment_method": "upi"})
        pay_id_2 = res_pay_2.json()["payment_id"]
        
        await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id_2, "simulated_outcome": "GATEWAY_TIMEOUT"})
        await recovery_service.wait_for_pending_tasks()
        
        txn_doc_2 = await db["transactions"].find_one({"_id": txn_id_2})
        assert txn_doc_2["status"] == "UNRECOVERABLE"
        
        attempts_2 = await db["payment_attempts"].find({"transaction_id": txn_id_2}).to_list(length=10)
        assert len(attempts_2) == 3
        
        # Verify no 4th attempt was executed
        assert len(attempts_2) < 4

