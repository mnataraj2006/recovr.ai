import pytest
from httpx import AsyncClient, ASGITransport
from tests.conftest import get_admin_headers
from app.main import app

@pytest.mark.asyncio
async def test_metrics_engine_calculations(db):
    """Verify that recovery rates, costs, and revenues are computed correctly."""
    # 1. Seed database with transactions
    # Txn 1: Recovered (₹2000)
    await db["transactions"].insert_one({
        "_id": "txn_recovered_1",
        "checkout_id": "chk_1",
        "customer_id": "cust_1",
        "amount": 2000.0,
        "status": "RECOVERED",
        "created_at": "2026-08-21T00:00:00Z"
    })
    # Txn 2: Unrecoverable (₹3000)
    await db["transactions"].insert_one({
        "_id": "txn_unrecovered_2",
        "checkout_id": "chk_2",
        "customer_id": "cust_2",
        "amount": 3000.0,
        "status": "UNRECOVERABLE",
        "created_at": "2026-08-21T00:00:00Z"
    })
    await db["payment_attempts"].insert_one({
        "_id": "att_rec_1",
        "transaction_id": "txn_recovered_1",
        "attempt_number": 2,
        "status": "Success"
    })
    
    # Seed recovery actions to verify cost calculations (1 nudge, 1 retry)
    await db["recovery_actions"].insert_one({
        "_id": "act_1",
        "transaction_id": "txn_recovered_1",
        "action_type": "NUDGE_CUSTOMER",
        "channel": "SMS",
        "status": "SUCCESS"
    })
    await db["recovery_actions"].insert_one({
        "_id": "act_2",
        "transaction_id": "txn_unrecovered_2",
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "FAILED"
    })
    
    # 2. Call Metrics Route
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=get_admin_headers()) as ac:
        res = await ac.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        
        # Risk = 2000 + 3000 = 5000
        assert data["total_revenue_at_risk"] == 5000.0
        # Recovered = 2000
        assert data["total_recovered_revenue"] == 2000.0
        # Transaction Recovery Rate = 1 / 2 = 0.5, Revenue Recovery Rate = 2000 / 5000 = 0.4
        assert data["transaction_recovery_rate"] == 0.5
        assert data["revenue_recovery_rate"] == 0.4
        # Cost = (1 * 0.50) + (1 * 1.00) = 1.50
        assert data["total_recovery_cost"] == 1.50
        # Net = 2000 - 1.50 = 1998.50
        assert data["net_recovered_revenue"] == 1998.50
        # ROI = 2000 / 1.50 = 1333.33
        assert data["roi"] == pytest.approx(1333.33, rel=1e-2)

@pytest.mark.asyncio
async def test_audit_logs_endpoints(db):
    """Verify that structured audit trails can be retrieved."""
    # Seed audit event
    await db["audit_events"].insert_one({
        "_id": "aud_1",
        "transaction_id": "txn_audit_test",
        "event_type": "PAYMENT_FAILED",
        "actor": "CUSTOMER",
        "source": "PaymentsAPI",
        "timestamp": "2026-08-21T00:00:00Z",
        "reason": "Card declined",
        "metadata": {}
    })
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=get_admin_headers()) as ac:
        # Test global stream
        res_global = await ac.get("/api/v1/audit-events")
        assert res_global.status_code == 200
        assert len(res_global.json()) >= 1
        
        # Test transaction stream
        res_txn = await ac.get("/api/v1/transactions/txn_audit_test/audit")
        assert res_txn.status_code == 200
        data = res_txn.json()
        assert data["transaction_id"] == "txn_audit_test"
        assert len(data["audit_events"]) == 1

@pytest.mark.asyncio
async def test_batch_cohort_simulation_run(db):
    """Verify that cohort batch simulations run and save summary reports successfully."""
    from app.services.auth_service import ensure_seed_user
    await ensure_seed_user(db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=get_admin_headers()) as ac:
        login_res = await ac.post("/api/v1/auth/login", json={"email": "admin@recovr.ai", "password": "Admin@123456"})
        token = login_res.json()["access_token"]
        # Trigger simulation run with admin token
        res = await ac.post("/api/v1/simulation/run", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 201

        report = res.json()
        
        # Verify cohort metrics
        assert "total_revenue_at_risk" in report
        assert "total_recovered_revenue" in report
        assert len(report["cohort_summary"]) == 5
        
        # Verify report was saved in MongoDB
        saved_report = await db["simulation_cohorts"].find_one({"_id": report["_id"]})
        assert saved_report is not None
        assert saved_report["total_revenue_at_risk"] == report["total_revenue_at_risk"]
