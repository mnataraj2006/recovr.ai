from fastapi import APIRouter, Depends
from app.db.connection import get_db

router = APIRouter()

@router.get("/metrics")
async def get_metrics(db = Depends(get_db)):
    """
    Calculates and returns revenue recovery performance metrics.
    """
    # 1. Status Distribution
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_cursor = db["transactions"].aggregate(pipeline)
    status_counts = {item["_id"]: item["count"] async for item in status_cursor}
    
    # 2. Identify transactions genuinely at risk:
    # - Has status in at_risk_statuses
    # - OR has at least one failed payment attempt
    # - OR has a recovery action proposed
    # - OR has been diagnosed
    at_risk_statuses = [
        "CHECKOUT_ABANDONED", "DIAGNOSING", "DIAGNOSED", "ACTION_PROPOSED", 
        "GUARDRAIL_CHECK", "APPROVED", "BLOCKED", "EXECUTING", 
        "RETRY_ESCALATE", "UNRECOVERABLE"
    ]
    failed_txn_ids = await db["payment_attempts"].distinct("transaction_id", {"status": "Failed"})
    action_txn_ids = await db["recovery_actions"].distinct("transaction_id")
    diagnosis_txn_ids = await db["diagnoses"].distinct("transaction_id")
    
    at_risk_filter = {
        "$or": [
            {"status": {"$in": at_risk_statuses}},
            {"_id": {"$in": failed_txn_ids}},
            {"_id": {"$in": action_txn_ids}},
            {"_id": {"$in": diagnosis_txn_ids}}
        ]
    }
    
    at_risk_txns = await db["transactions"].find(at_risk_filter).to_list(length=10000)
    total_revenue_at_risk = sum(t["amount"] for t in at_risk_txns)
    
    # 3. Total Recovered Revenue (Transactions in at_risk set that now have status RECOVERED or SUCCESS)
    recovered_txns = [t for t in at_risk_txns if t["status"] in ["RECOVERED", "SUCCESS"]]
    total_recovered_revenue = sum(t["amount"] for t in recovered_txns)
    
    # 4. Recovery Rates
    revenue_recovery_rate = (total_recovered_revenue / total_revenue_at_risk) if total_revenue_at_risk > 0 else 0.0
    transaction_recovery_rate = (len(recovered_txns) / len(at_risk_txns)) if len(at_risk_txns) > 0 else 0.0
    
    # 5. Recovery Costs
    # SMS/WhatsApp = ₹0.50, Email = ₹0.10, API Retries = ₹1.00
    actions = await db["recovery_actions"].find({}).to_list(length=10000)
    total_recovery_cost = 0.0
    nudge_count = 0
    retry_count = 0
    for action in actions:
        action_type = action.get("action_type")
        channel = action.get("channel")
        if action_type == "RETRY_PAYMENT":
            retry_count += 1
            total_recovery_cost += 1.00
        elif action_type == "NUDGE_CUSTOMER":
            nudge_count += 1
            if channel == "EMAIL":
                total_recovery_cost += 0.10
            elif channel in ["SMS", "WHATSAPP"]:
                total_recovery_cost += 0.50
            else:
                total_recovery_cost += 0.50  # Default cost
                
    net_recovered_revenue = total_recovered_revenue - total_recovery_cost
    
    # 6. ROI = (Revenue Recovered - Recovery Cost) / Recovery Cost
    roi = ((total_recovered_revenue - total_recovery_cost) / total_recovery_cost) if total_recovery_cost > 0 else 0.0
    
    # 7. Grouped by Diagnosis Root Cause
    pipeline_cause = [{"$group": {"_id": "$root_cause", "count": {"$sum": 1}}}]
    cause_cursor = db["diagnoses"].aggregate(pipeline_cause)
    cause_distribution = {item["_id"]: item["count"] async for item in cause_cursor}
    
    return {
        "total_revenue_at_risk": total_revenue_at_risk,
        "total_recovered_revenue": total_recovered_revenue,
        "net_recovered_revenue": net_recovered_revenue,
        "recovery_rate": revenue_recovery_rate,
        "revenue_recovery_rate": revenue_recovery_rate,
        "transaction_recovery_rate": transaction_recovery_rate,
        "total_recovery_cost": total_recovery_cost,
        "roi": roi,
        "nudge_count": nudge_count,
        "retry_count": retry_count,
        "status_distribution": status_counts,
        "cause_distribution": cause_distribution
    }
