import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from httpx import AsyncClient
from app.db.connection import get_db
from app.services.recovery_service import recovery_service

logger = logging.getLogger(__name__)

COHORT_PROFILES = [
    {
        "name": "Transaction 1 - Initial Success",
        "email": "txn1@example.com",
        "phone": "+919000000001",
        "amount": 1000.0,
        "failure_mode": "SUCCESS",
        "simulated_outcomes": ["SUCCESS"]
    },
    {
        "name": "Transaction 2 - Gateway Timeout Recovered",
        "email": "txn2@example.com",
        "phone": "+919000000002",
        "amount": 2000.0,
        "failure_mode": "GATEWAY_TIMEOUT",
        "simulated_outcomes": ["GATEWAY_TIMEOUT", "SUCCESS"]
    },
    {
        "name": "Transaction 3 - Gateway Timeout Unrecoverable",
        "email": "txn3@example.com",
        "phone": "+919000000003",
        "amount": 3000.0,
        "failure_mode": "DOUBLE_ATTEMPT_BLOCK",
        "simulated_outcomes": ["GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT", "GATEWAY_TIMEOUT"]
    },
    {
        "name": "Transaction 4 - Abandoned Customer Does Not Return",
        "email": "txn4@example.com",
        "phone": "+919000000004",
        "amount": 4000.0,
        "failure_mode": "ABANDON_NO_RETURN",
        "customer_response": "DOES_NOT_RETURN",
        "simulated_outcomes": []
    },
    {
        "name": "Transaction 5 - Abandoned Customer Returns & Pays",
        "email": "txn5@example.com",
        "phone": "+919000000005",
        "amount": 5000.0,
        "failure_mode": "ABANDON",
        "customer_response": "RETURNS",
        "simulated_outcomes": ["SUCCESS"]
    }
]

class SimulationRunner:
    async def run_batch_cohort(self, seed: Optional[int] = 42) -> dict:
        """
        Runs an asynchronous batch simulation for a deterministic cohort of 5 customers,
        evaluates all recovery flows concurrently, and aggregates results.
        """
        if seed is not None:
            import random
            random.seed(seed)
            
        simulation_id = f"sim_{uuid.uuid4().hex[:8]}"
        logger.info(f"SimulationRunner: Launching batch cohort {simulation_id}")
        
        db = await get_db()
        from app.main import app
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            tasks = []
            for profile in COHORT_PROFILES:
                tasks.append(self._simulate_customer_flow(ac, profile))
                
            # Execute all simulation flows concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait for all background recovery orchestrations to finish writing
            await recovery_service.wait_for_pending_tasks()
            
            # 3. Fetch outcomes and calculate metrics from actual DB records
            txn_ids = [res["transaction_id"] for res in results if isinstance(res, dict) and "transaction_id" in res]
            
            cohort_txns = await db["transactions"].find({"_id": {"$in": txn_ids}}).to_list(length=10)
            cohort_actions = await db["recovery_actions"].find({"transaction_id": {"$in": txn_ids}}).to_list(length=20)
            cohort_decisions = await db["guardrail_decisions"].find({"transaction_id": {"$in": txn_ids}}).to_list(length=20)
            
            total_transactions = len(cohort_txns)
            total_transaction_value = sum(t["amount"] for t in cohort_txns)
            
            at_risk_statuses = [
                "CHECKOUT_ABANDONED", "DIAGNOSING", "DIAGNOSED", "ACTION_PROPOSED", 
                "GUARDRAIL_CHECK", "APPROVED", "BLOCKED", "EXECUTING", 
                "RETRY_ESCALATE", "UNRECOVERABLE"
            ]
            cohort_diagnoses = await db["diagnoses"].find({"transaction_id": {"$in": txn_ids}}).to_list(length=20)
            cohort_attempts = await db["payment_attempts"].find({"transaction_id": {"$in": txn_ids}}).to_list(length=50)
            
            action_txn_ids = set(a["transaction_id"] for a in cohort_actions)
            diagnosis_txn_ids = set(d["transaction_id"] for d in cohort_diagnoses)
            failed_txn_ids = set(p["transaction_id"] for p in cohort_attempts if p.get("status") == "Failed")
            success_txn_ids = set(p["transaction_id"] for p in cohort_attempts if p.get("status") == "Success")
            
            at_risk_txns = []
            for t in cohort_txns:
                t_id = t["_id"]
                status = t["status"]
                if (status in at_risk_statuses or 
                    status == "RECOVERED" or
                    t_id in failed_txn_ids or 
                    t_id in action_txn_ids or 
                    t_id in diagnosis_txn_ids):
                    at_risk_txns.append(t)
            at_risk_transactions = len(at_risk_txns)
            revenue_at_risk = sum(t["amount"] for t in at_risk_txns)
            
            recovered_txns = [t for t in at_risk_txns if t["status"] == "RECOVERED" or (t["status"] == "SUCCESS" and t["_id"] in success_txn_ids)]
            recovered_transactions = len(recovered_txns)
            recovered_revenue = sum(t["amount"] for t in recovered_txns)
            
            normal_success_txns = [t for t in cohort_txns if t not in at_risk_txns and t["status"] == "SUCCESS"]
            normal_success_revenue = sum(t["amount"] for t in normal_success_txns)
            
            transaction_recovery_rate = (recovered_transactions / at_risk_transactions) if at_risk_transactions > 0 else 0.0
            revenue_recovery_rate = (recovered_revenue / revenue_at_risk) if revenue_at_risk > 0 else 0.0
            
            # Recovery Costs
            total_recovery_cost = 0.0
            nudge_count = 0
            retry_count = 0
            for a in cohort_actions:
                a_type = a.get("action_type")
                channel = a.get("channel")
                if a_type == "RETRY_PAYMENT":
                    retry_count += 1
                    total_recovery_cost += 1.00
                elif a_type == "NUDGE_CUSTOMER":
                    nudge_count += 1
                    if channel == "EMAIL":
                        total_recovery_cost += 0.10
                    elif channel in ["SMS", "WHATSAPP"]:
                        total_recovery_cost += 0.50
                    else:
                        total_recovery_cost += 0.50
                        
            net_recovered_revenue = recovered_revenue - total_recovery_cost
            roi = ((recovered_revenue - total_recovery_cost) / total_recovery_cost) if total_recovery_cost > 0 else 0.0
            
            cohort_summary = []
            for t in cohort_txns:
                txn_id = t["_id"]
                matching_res = next((r for r in results if r["transaction_id"] == txn_id), {})
                matching_action = next((a for a in cohort_actions if a["transaction_id"] == txn_id), None)
                matching_decision = next((d for d in cohort_decisions if d["transaction_id"] == txn_id), None)
                
                cohort_summary.append({
                    "transaction_id": txn_id,
                    "customer_name": matching_res.get("name", "Unknown"),
                    "amount": t["amount"],
                    "failure_mode": matching_res.get("failure_mode", "UNKNOWN"),
                    "status": t["status"],
                    "action_proposed": matching_action["action_type"] if matching_action else "None",
                    "guardrail_decision": "Approved" if (matching_decision and matching_decision["allowed"]) else ("Blocked" if matching_decision else "N/A"),
                    "reason": matching_decision["reason"] if matching_decision else "N/A"
                })
                
            report = {
                "_id": simulation_id,
                "created_at": datetime.now(timezone.utc),
                "total_transactions": total_transactions,
                "at_risk_transactions": at_risk_transactions,
                "recovered_transactions": recovered_transactions,
                "transaction_recovery_rate": transaction_recovery_rate,
                "total_transaction_value": total_transaction_value,
                "total_revenue_at_risk": revenue_at_risk,
                "revenue_at_risk": revenue_at_risk,
                "total_recovered_revenue": recovered_revenue,
                "recovered_revenue": recovered_revenue,
                "normal_success_revenue": normal_success_revenue,
                "revenue_recovery_rate": revenue_recovery_rate,
                "net_recovered_revenue": net_recovered_revenue,
                "recovery_rate": transaction_recovery_rate,
                "total_recovery_cost": total_recovery_cost,
                "roi": roi,
                "nudge_count": nudge_count,
                "retry_count": retry_count,
                "cohort_summary": cohort_summary
            }
            
            await db["simulation_cohorts"].insert_one(report)
            return report

    async def _simulate_customer_flow(self, ac: AsyncClient, profile: dict) -> dict:
        """Simulates checkout lifecycle for a single customer profile."""
        # Step 1: Create Checkout
        checkout_payload = {
            "customer": {
                "name": profile["name"],
                "email": profile["email"],
                "phone": profile["phone"]
            },
            "cart_value": profile["amount"],
            "items": [],
            "simulated_outcomes": profile.get("simulated_outcomes")
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        chk_data = res_chk.json()
        txn_id = chk_data["transaction_id"]
        chk_id = chk_data["checkout_id"]
        
        # Step 2: Handle checkout abandonment vs payment failure modes
        if profile["failure_mode"] in ["ABANDON", "ABANDON_NO_RETURN"]:
            abandon_payload = {
                "checkout_duration_seconds": 180.0,
                "last_viewed_step": "shipping",
                "selected_payment_method": None
            }
            await ac.post(f"/api/v1/checkouts/{chk_id}/abandon", json=abandon_payload)
            
        elif profile["failure_mode"] == "DOUBLE_ATTEMPT_BLOCK":
            # Direct insert 2 failed attempts to trigger guardrail cap block safely
            res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
            pay_id = res_pay.json()["payment_id"]
            
            db = await get_db()
            for i in range(3):
                await db["payment_attempts"].insert_one({
                    "_id": f"att_sim_{uuid.uuid4().hex[:8]}",
                    "transaction_id": txn_id,
                    "attempt_number": i + 1,
                    "status": "Failed",
                    "gateway_reference": f"ref_sim_{i}",
                    "payment_method": "upi",
                    "gateway_error_code": "GATEWAY_TIMEOUT",
                    "gateway_error_reason": "gateway_timeout",
                    "gateway_error_message": "Gateway connection timed out before bank response received.",
                    "created_at": datetime.now(timezone.utc),
                    "completed_at": datetime.now(timezone.utc)
                })
            
            # Trigger process_failed_payment directly (will get blocked by retry cap guardrail)
            task = asyncio.create_task(
                recovery_service.process_failed_payment(
                    txn_id,
                    error_code="GATEWAY_TIMEOUT",
                    error_description="Connection lost",
                    fast_mode=True
                )
            )
            recovery_service.track_task(task)
            
        else:
            # Payment Failure flows
            res_pay = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "upi"})
            pay_id = res_pay.json()["payment_id"]
            await ac.post("/api/v1/payments/attempt", json={"payment_id": pay_id, "simulated_outcome": profile["failure_mode"]})
            
        return {
            "transaction_id": txn_id,
            "name": profile["name"],
            "failure_mode": profile["failure_mode"]
        }

simulation_runner = SimulationRunner()
