import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.main import app
from app.engines.guardrails.engine import guardrail_engine
from app.engines.scheduler.engine import retry_scheduler
from app.models.transaction import Transaction

@pytest.mark.asyncio
async def test_guardrail_duplicate_payment_block(db):
    """Verify that guardrail blocks action if a payment has already succeeded."""
    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    checkout_id = f"chk_{uuid.uuid4().hex[:8]}"
    
    # Insert transaction in GUARDRAIL_CHECK status
    txn = Transaction(
        id=txn_id,
        checkout_id=checkout_id,
        customer_id="cust_123",
        amount=1500.0,
        status="GUARDRAIL_CHECK"
    )
    txn_doc = txn.model_dump()
    txn_doc["_id"] = txn_doc.pop("id")
    await db["transactions"].insert_one(txn_doc)
    
    # Insert a successful payment attempt
    attempt_doc = {
        "_id": f"att_{uuid.uuid4().hex[:8]}",
        "transaction_id": txn_id,
        "attempt_number": 1,
        "status": "Success",
        "gateway_reference": "ref_123",
        "payment_method": "upi",
        "created_at": datetime.now(timezone.utc)
    }
    await db["payment_attempts"].insert_one(attempt_doc)
    
    # Propose a retry action
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    action_doc = {
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc)
    }
    await db["recovery_actions"].insert_one(action_doc)
    
    # Run Guardrail verify
    res = await guardrail_engine.verify_action(action_id)
    assert res["allowed"] is False
    assert "already has a successful payment" in res["reason"]
    
    # Assert transaction state updated to UNRECOVERABLE
    txn_final = await db["transactions"].find_one({"_id": txn_id})
    assert txn_final["status"] == "UNRECOVERABLE"

@pytest.mark.asyncio
async def test_guardrail_retry_limit_exceeded(db):
    """Verify that guardrail blocks retry if max retry limit (2) is exceeded."""
    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    checkout_id = f"chk_{uuid.uuid4().hex[:8]}"
    
    txn = Transaction(
        id=txn_id,
        checkout_id=checkout_id,
        customer_id="cust_123",
        amount=1500.0,
        status="GUARDRAIL_CHECK"
    )
    txn_doc = txn.model_dump()
    txn_doc["_id"] = txn_doc.pop("id")
    await db["transactions"].insert_one(txn_doc)
    
    # Insert 2 failed payment attempts
    for i in range(2):
        await db["payment_attempts"].insert_one({
            "_id": f"att_{uuid.uuid4().hex[:8]}",
            "transaction_id": txn_id,
            "attempt_number": i + 1,
            "status": "Failed",
            "gateway_reference": f"ref_{i}",
            "payment_method": "upi",
            "created_at": datetime.now(timezone.utc)
        })
        
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    action_doc = {
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "RETRY_PAYMENT",
        "channel": "API_RETRY",
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc)
    }
    await db["recovery_actions"].insert_one(action_doc)
    
    res = await guardrail_engine.verify_action(action_id)
    assert res["allowed"] is False
    assert "retry cap (2 attempts) exceeded" in res["reason"]

@pytest.mark.asyncio
async def test_guardrail_cooldown_window_violation(db):
    """Verify that guardrail blocks nudge if cooldown window (5 mins) is violated."""
    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    checkout_id = f"chk_{uuid.uuid4().hex[:8]}"
    
    txn = Transaction(
        id=txn_id,
        checkout_id=checkout_id,
        customer_id="cust_123",
        amount=1500.0,
        status="GUARDRAIL_CHECK"
    )
    txn_doc = txn.model_dump()
    txn_doc["_id"] = txn_doc.pop("id")
    await db["transactions"].insert_one(txn_doc)
    
    # Insert diagnosis record (allowing up to 2 nudges)
    await db["diagnoses"].insert_one({
        "_id": f"diag_{uuid.uuid4().hex[:8]}",
        "transaction_id": txn_id,
        "root_cause": "PRICE_HESITATION",
        "confidence": 1.0,
        "source": "RULE_ENGINE",
        "reasoning": "Under PRICE_HESITATION we permit up to 2 nudges, triggering cooldown validation on nudge 2.",
        "created_at": datetime.now(timezone.utc)
    })
    
    # Insert a nudge sent 1 minute ago
    await db["recovery_actions"].insert_one({
        "_id": f"act_old_{uuid.uuid4().hex[:8]}",
        "transaction_id": txn_id,
        "action_type": "NUDGE_CUSTOMER",
        "channel": "SMS",
        "status": "SUCCESS",
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=1)
    })
    
    # Propose new nudge
    action_id = f"act_new_{uuid.uuid4().hex[:8]}"
    action_doc = {
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "NUDGE_CUSTOMER",
        "channel": "SMS",
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc)
    }
    await db["recovery_actions"].insert_one(action_doc)
    
    # Run Guardrail verification (with cooldown active)
    res = await guardrail_engine.verify_action(action_id, skip_cooldown_for_test=False)
    assert res["allowed"] is False
    assert "cooldown" in res["reason"]

@pytest.mark.asyncio
async def test_guardrail_incentive_limit_violation(db):
    """Verify that guardrail blocks incentives exceeding 10% value or ₹500 cap."""
    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    checkout_id = f"chk_{uuid.uuid4().hex[:8]}"
    
    txn = Transaction(
        id=txn_id,
        checkout_id=checkout_id,
        customer_id="cust_123",
        amount=1000.0,  # 10% is ₹100
        status="GUARDRAIL_CHECK"
    )
    txn_doc = txn.model_dump()
    txn_doc["_id"] = txn_doc.pop("id")
    await db["transactions"].insert_one(txn_doc)
    
    # Propose a nudge with a ₹150 incentive (15% of ₹1000 - illegal!)
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    action_doc = {
        "_id": action_id,
        "transaction_id": txn_id,
        "action_type": "NUDGE_CUSTOMER",
        "channel": "SMS",
        "status": "PENDING",
        "payload": {
            "incentive": {
                "type": "discount",
                "value": 150.0
            }
        },
        "created_at": datetime.now(timezone.utc)
    }
    await db["recovery_actions"].insert_one(action_doc)
    
    res = await guardrail_engine.verify_action(action_id)
    assert res["allowed"] is False
    assert "exceeds allowed threshold" in res["reason"]

@pytest.mark.asyncio
async def test_end_to_end_auto_retry_recovery_integration(db):
    """Test full integration: Failure webhook -> Diagnosis -> Policy -> Guardrails -> Scheduler Retry -> Success."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Create Checkout
        checkout_payload = {
            "customer": {
                "name": "Alex Recoverable",
                "email": "alex@example.com",
                "phone": "+919555566666"
            },
            "cart_value": 3500.0,
            "items": []
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        chk_data = res_chk.json()
        txn_id = chk_data["transaction_id"]
        chk_id = chk_data["checkout_id"]
        
        # 2. Create Payment Intent
        payment_payload = {
            "transaction_id": txn_id,
            "payment_method": "upi",
            "upi_provider": "gpay"
        }
        res_pay = await ac.post("/api/v1/payments/create", json=payment_payload)
        payment_id = res_pay.json()["payment_id"]
        
        # 3. Attempt Payment with simulated GATEWAY_TIMEOUT (triggers background recovery pipeline automatically!)
        attempt_payload = {
            "payment_id": payment_id,
            "simulated_outcome": "GATEWAY_TIMEOUT"
        }
        res_att = await ac.post("/api/v1/payments/attempt", json=attempt_payload)
        assert res_att.status_code == 200
        assert res_att.json()["success"] is False
        
        # Wait for all background tasks to complete before assertions
        from app.services.recovery_service import recovery_service
        await recovery_service.wait_for_pending_tasks()
        
        # 4. Verify Outcome in Database
        # Check transaction state is now RECOVERED
        txn_doc = await db["transactions"].find_one({"_id": txn_id})
        assert txn_doc["status"] == "RECOVERED"
        
        # Check payment attempts: 2 total (1 failed, 1 success)
        attempts_list = await db["payment_attempts"].find({"transaction_id": txn_id}).sort("attempt_number", 1).to_list(length=10)
        assert len(attempts_list) == 2
        assert attempts_list[0]["status"] == "Failed"
        assert attempts_list[0]["gateway_error_code"] == "GATEWAY_TIMEOUT"
        assert attempts_list[1]["status"] == "Success"
        
        # Check guardrail decisions logged
        decision = await db["guardrail_decisions"].find_one({"transaction_id": txn_id})
        assert decision is not None
        assert decision["allowed"] is True
        
        # Check audit event logged showing recovery completion
        recovery_audit = await db["audit_events"].find_one({
            "transaction_id": txn_id,
            "event_type": "PAYMENT_RECOVERED"
        })
        assert recovery_audit is not None
