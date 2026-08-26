import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from tests.conftest import get_admin_headers
from app.main import app
from app.simulation.runner import simulation_runner

@pytest.mark.asyncio
async def test_case_1_normal_success_is_not_recovery(db):
    """Case 1: Normal initial SUCCESS is NOT counted as recovery."""
    await db["transactions"].delete_many({})
    await db["payment_attempts"].delete_many({})
    
    txn_id = f"txn_norm_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_norm",
        "customer_id": "cust_norm",
        "amount": 1000.0,
        "status": "SUCCESS"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_id,
        "attempt_number": 1,
        "status": "Success"
    })
    
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        res = await ac.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        
        assert data["total_transactions"] == 1
        assert data["at_risk_transactions"] == 0
        assert data["recovered_transactions"] == 0
        assert data["recovered_revenue"] == 0.0
        assert data["normal_success_revenue"] == 1000.0
        assert data["transaction_recovery_rate"] == 0.0

@pytest.mark.asyncio
async def test_case_2_failed_then_successful_retry_is_recovery(db):
    """Case 2: Failed initial payment -> successful retry is recovery."""
    await db["transactions"].delete_many({})
    await db["payment_attempts"].delete_many({})
    
    txn_id = f"txn_rec_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_rec",
        "customer_id": "cust_rec",
        "amount": 2000.0,
        "status": "RECOVERED"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_1_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_id,
        "attempt_number": 1,
        "status": "Failed",
        "gateway_error_code": "GATEWAY_TIMEOUT"
    })
    await db["payment_attempts"].insert_one({
        "_id": f"att_2_{uuid.uuid4().hex[:6]}",
        "transaction_id": txn_id,
        "attempt_number": 2,
        "status": "Success"
    })
    
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        res = await ac.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        
        assert data["at_risk_transactions"] == 1
        assert data["recovered_transactions"] == 1
        assert data["recovered_revenue"] == 2000.0
        assert data["transaction_recovery_rate"] == 1.0

@pytest.mark.asyncio
async def test_case_3_invalid_recovery_detected(db):
    """Case 3: RECOVERED status without payment attempt success detected as invalid."""
    await db["transactions"].delete_many({})
    await db["payment_attempts"].delete_many({})
    
    txn_id = f"txn_inv_{uuid.uuid4().hex[:6]}"
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_inv",
        "customer_id": "cust_inv",
        "amount": 3000.0,
        "status": "RECOVERED"  # Fraudulent / corrupt state
    })
    # No payment attempts inserted
    
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        res = await ac.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        
        assert data["invalid_recovered_transactions"] == 1
        assert data["recovered_transactions"] == 0
        assert data["recovered_revenue"] == 0.0

@pytest.mark.asyncio
async def test_case_4_5_6_nudge_flow_outcomes(db):
    """Case 4, 5, 6: Test Nudge response variations (Returns + Success, Returns + Failure, No Return)."""
    await db["transactions"].delete_many({})
    await db["payment_attempts"].delete_many({})
    await db["recovery_actions"].delete_many({})
    await db["diagnoses"].delete_many({})
    
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        # Case 4: Nudge + Returns + Success = Recovery
        res_4 = await ac.post("/api/v1/checkouts", json={
            "customer": {"name": "Cust 4", "email": "c4@ex.com", "phone": "+919000000004"},
            "cart_value": 2500.0,
            "simulated_outcomes": ["SUCCESS"],
            "customer_response": "RETURNS"
        })
        chk_4_id = res_4.json()["checkout_id"]
        txn_4_id = res_4.json()["transaction_id"]
        
        # Case 5: Nudge + Returns + Failure = Not Recovered
        res_5 = await ac.post("/api/v1/checkouts", json={
            "customer": {"name": "Cust 5", "email": "c5@ex.com", "phone": "+919000000005"},
            "cart_value": 2500.0,
            "simulated_outcomes": ["GATEWAY_TIMEOUT"],
            "customer_response": "RETURNS"
        })
        chk_5_id = res_5.json()["checkout_id"]
        txn_5_id = res_5.json()["transaction_id"]
        
        # Case 6: Nudge + No Return = Not Recovered (0 payment attempts)
        res_6 = await ac.post("/api/v1/checkouts", json={
            "customer": {"name": "Cust 6", "email": "c6@ex.com", "phone": "+919000000006"},
            "cart_value": 2500.0,
            "simulated_outcomes": [],
            "customer_response": "DOES_NOT_RETURN"
        })
        chk_6_id = res_6.json()["checkout_id"]
        txn_6_id = res_6.json()["transaction_id"]

        await ac.post(f"/api/v1/checkouts/{chk_4_id}/abandon", json={"checkout_duration_seconds": 120.0})
        await ac.post(f"/api/v1/checkouts/{chk_5_id}/abandon", json={"checkout_duration_seconds": 120.0})
        await ac.post(f"/api/v1/checkouts/{chk_6_id}/abandon", json={"checkout_duration_seconds": 120.0})
        
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        # Verify Case 4: Txn 4 is RECOVERED
        doc_4 = await db["transactions"].find_one({"_id": txn_4_id})
        assert doc_4["status"] == "RECOVERED"
        att_4_count = await db["payment_attempts"].count_documents({"transaction_id": txn_4_id})
        assert att_4_count == 1
        
        # Verify Case 5: Txn 5 is NOT RECOVERED
        doc_5 = await db["transactions"].find_one({"_id": txn_5_id})
        assert doc_5["status"] != "RECOVERED"
        att_5_count = await db["payment_attempts"].count_documents({"transaction_id": txn_5_id})
        assert att_5_count >= 1
        
        # Verify Case 6: Txn 6 has 0 payment attempts and is NOT RECOVERED
        doc_6 = await db["transactions"].find_one({"_id": txn_6_id})
        assert doc_6["status"] != "RECOVERED"
        att_6_count = await db["payment_attempts"].count_documents({"transaction_id": txn_6_id})
        assert att_6_count == 0

@pytest.mark.asyncio
async def test_case_7_8_customer_return_idempotency(db):
    """Case 7 & 8: Single payment attempt created per return and recovery execution idempotency."""
    txn_id = f"txn_idemp_{uuid.uuid4().hex[:6]}"
    action_id = f"act_idemp_{uuid.uuid4().hex[:6]}"
    
    await db["transactions"].insert_one({
        "_id": txn_id,
        "checkout_id": "chk_idemp",
        "customer_id": "cust_idemp",
        "amount": 1000.0,
        "status": "EXECUTING",
        "customer_response": "RETURNS",
        "simulated_outcomes": ["SUCCESS"]
    })
    await db["recovery_actions"].insert_one({
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "NUDGE_CUSTOMER",
        "channel": "EMAIL",
        "status": "APPROVED"
    })
    
    from app.services.recovery_service import recovery_service
    # Run twice
    await recovery_service._execute_simulated_customer_nudge(txn_id, action_id)
    await recovery_service._execute_simulated_customer_nudge(txn_id, action_id)
    
    # Assert exactly 1 payment attempt was created
    att_count = await db["payment_attempts"].count_documents({"transaction_id": txn_id})
    assert att_count == 1

@pytest.mark.asyncio
async def test_case_9_10_11_14_deterministic_cohort_verification(db):
    """Case 9, 10, 11, 14: Run batch cohort and verify metrics, database, and API match exact Part 7 expectations."""
    await db["transactions"].delete_many({})
    await db["payment_attempts"].delete_many({})
    await db["recovery_actions"].delete_many({})
    await db["guardrail_decisions"].delete_many({})
    await db["simulation_cohorts"].delete_many({})
    
    # Run deterministic batch simulation
    report = await simulation_runner.run_batch_cohort(seed=42)
    
    # Invariant assertions on report output
    assert report["total_transactions"] == 5
    assert report["at_risk_transactions"] == 4
    assert report["recovered_transactions"] == 2
    assert abs(report["transaction_recovery_rate"] - 0.5) < 0.0001
    assert report["total_transaction_value"] == 15000.0
    assert report["revenue_at_risk"] == 14000.0
    assert report["recovered_revenue"] == 7000.0
    assert abs(report["revenue_recovery_rate"] - 0.5) < 0.0001
    assert report["normal_success_revenue"] == 1000.0
    
    # Direct MongoDB query verification
    db_all = await db["transactions"].find({}).to_list(length=10)
    assert len(db_all) == 5
    
    # Fetch Metrics via API and verify API values match DB-derived values
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        res = await ac.get("/api/v1/metrics")
        assert res.status_code == 200
        api_data = res.json()
        
        assert api_data["total_transactions"] == report["total_transactions"]
        assert api_data["at_risk_transactions"] == report["at_risk_transactions"]
        assert api_data["recovered_transactions"] == report["recovered_transactions"]
        assert abs(api_data["transaction_recovery_rate"] - report["transaction_recovery_rate"]) < 0.0001
        assert api_data["revenue_at_risk"] == report["revenue_at_risk"]
        assert api_data["recovered_revenue"] == report["recovered_revenue"]
        assert abs(api_data["revenue_recovery_rate"] - report["revenue_recovery_rate"]) < 0.0001
        assert api_data["normal_success_revenue"] == report["normal_success_revenue"]

@pytest.mark.asyncio
async def test_case_12_13_zero_division_safety(db):
    """Case 12 & 13: Zero at-risk transactions and zero revenue at risk handling."""
    await db["transactions"].delete_many({})
    await db["payment_attempts"].delete_many({})
    
    async with AsyncClient(app=app, base_url="http://test", headers=get_admin_headers()) as ac:
        res = await ac.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        
        assert data["at_risk_transactions"] == 0
        assert data["revenue_at_risk"] == 0.0
        assert data["transaction_recovery_rate"] == 0.0
        assert data["revenue_recovery_rate"] == 0.0
        assert data["roi"] == 0.0
