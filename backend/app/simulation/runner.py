import uuid
import asyncio
import logging
from datetime import datetime, timezone
from httpx import AsyncClient
from app.db.connection import get_db
from app.services.recovery_service import recovery_service

logger = logging.getLogger(__name__)

COHORT_PROFILES = [
    {
        "name": "Arjun Sharma",
        "email": "arjun.sharma@example.com",
        "phone": "+919988877666",
        "amount": 4200.0,
        "failure_mode": "GATEWAY_TIMEOUT"  # Triggers Auto-retry -> success
    },
    {
        "name": "Priya Patel",
        "email": "priya.patel@example.com",
        "phone": "+919876543219",
        "amount": 1500.0,
        "failure_mode": "INSUFFICIENT_FUNDS"  # Triggers Customer Nudge -> success
    },
    {
        "name": "Rohan Das",
        "email": "rohan.das@example.com",
        "phone": "+919555512345",
        "amount": 750.0,
        "failure_mode": "ABANDON"  # Cart abandonment -> Nudge -> success
    },
    {
        "name": "Sneha Reddy",
        "email": "sneha.reddy@example.com",
        "phone": "+919222233333",
        "amount": 5500.0,
        "failure_mode": "INCORRECT_OTP"  # Triggers Nudge with Incentive -> success
    },
    {
        "name": "Vikram Singh",
        "email": "vikram.singh@example.com",
        "phone": "+919111122222",
        "amount": 3200.0,
        "failure_mode": "DOUBLE_ATTEMPT_BLOCK"  # Force retry cap / blocked action -> UNRECOVERABLE
    }
]

class SimulationRunner:
    async def run_batch_cohort(self) -> dict:
        """
        Runs an asynchronous batch simulation for a cohort of 5 customers,
        evaluates all recovery flows concurrently, and aggregates results.
        """
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
            
            # 3. Fetch outcomes and calculate metrics
            txn_ids = [res["transaction_id"] for res in results if isinstance(res, dict) and "transaction_id" in res]
            
            cohort_txns = await db["transactions"].find({"_id": {"$in": txn_ids}}).to_list(length=10)
            cohort_actions = await db["recovery_actions"].find({"transaction_id": {"$in": txn_ids}}).to_list(length=20)
            cohort_decisions = await db["guardrail_decisions"].find({"transaction_id": {"$in": txn_ids}}).to_list(length=20)
            
            total_revenue_at_risk = sum(t["amount"] for t in cohort_txns)
            total_recovered_revenue = sum(t["amount"] for t in cohort_txns if t["status"] in ["RECOVERED", "SUCCESS"])
            recovery_rate = (total_recovered_revenue / total_revenue_at_risk) if total_revenue_at_risk > 0 else 0.0
            
            # Recovery Costs
            nudge_count = sum(1 for a in cohort_actions if a["action_type"] == "NUDGE_CUSTOMER")
            retry_count = sum(1 for a in cohort_actions if a["action_type"] == "RETRY_PAYMENT")
            total_recovery_cost = (nudge_count * 0.50) + (retry_count * 1.00)
            net_recovered_revenue = total_recovered_revenue - total_recovery_cost
            roi = (total_recovered_revenue / total_recovery_cost) if total_recovery_cost > 0 else 0.0
            
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
                "total_revenue_at_risk": total_revenue_at_risk,
                "total_recovered_revenue": total_recovered_revenue,
                "net_recovered_revenue": net_recovered_revenue,
                "recovery_rate": recovery_rate,
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
            "items": []
        }
        res_chk = await ac.post("/api/v1/checkouts", json=checkout_payload)
        chk_data = res_chk.json()
        txn_id = chk_data["transaction_id"]
        chk_id = chk_data["checkout_id"]
        
        # Step 2: Handle checkout abandonment vs payment failure modes
        if profile["failure_mode"] == "ABANDON":
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
                    "created_at": datetime.now(timezone.utc)
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
