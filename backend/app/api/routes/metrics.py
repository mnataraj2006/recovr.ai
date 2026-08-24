from fastapi import APIRouter, Depends
from app.db.connection import get_db

router = APIRouter()

@router.get("/metrics")
async def get_metrics(db = Depends(get_db)):
    """
    Calculates and returns revenue recovery performance metrics.
    """
    # 1. Total Transactions & Total Value
    all_txns = await db["transactions"].find({}).to_list(length=10000)
    total_transactions = len(all_txns)
    total_transaction_value = sum(t["amount"] for t in all_txns)
    
    # 2. Status Distribution
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_cursor = db["transactions"].aggregate(pipeline)
    status_counts = {item["_id"]: item["count"] async for item in status_cursor}
    
    # 3. Identify transactions genuinely AT RISK
    at_risk_statuses = [
        "CHECKOUT_ABANDONED", "DIAGNOSING", "DIAGNOSED", "ACTION_PROPOSED", 
        "GUARDRAIL_CHECK", "APPROVED", "BLOCKED", "EXECUTING", 
        "RETRY_ESCALATE", "UNRECOVERABLE"
    ]
    failed_txn_ids = set(await db["payment_attempts"].distinct("transaction_id", {"status": "Failed"}))
    action_txn_ids = set(await db["recovery_actions"].distinct("transaction_id"))
    diagnosis_txn_ids = set(await db["diagnoses"].distinct("transaction_id"))
    
    at_risk_txns = []
    for t in all_txns:
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
    
    # 4. Identify genuinely RECOVERED transactions & integrity checks
    success_txn_ids = set(await db["payment_attempts"].distinct("transaction_id", {"status": "Success"}))
    at_risk_ids = set(t["_id"] for t in at_risk_txns)
    
    recovered_txns = []
    invalid_recovered_txns = []
    
    for t in all_txns:
        t_id = t["_id"]
        status = t["status"]
        if status == "RECOVERED":
            if t_id in success_txn_ids and t_id in at_risk_ids:
                recovered_txns.append(t)
            else:
                invalid_recovered_txns.append(t)
        elif status == "SUCCESS":
            if t_id in at_risk_ids and t_id in success_txn_ids:
                recovered_txns.append(t)
                
    recovered_transactions = len(recovered_txns)
    invalid_recovered_transactions = len(invalid_recovered_txns)
    recovered_revenue = sum(t["amount"] for t in recovered_txns)
    
    # Calculate normal initial success revenue (non-at-risk SUCCESS transactions)
    normal_success_txns = [t for t in all_txns if t["_id"] not in at_risk_ids and t["status"] == "SUCCESS"]
    normal_success_revenue = sum(t["amount"] for t in normal_success_txns)
    
    # 5. Recovery Rates (ratios: 0.0 to 1.0)
    transaction_recovery_rate = (recovered_transactions / at_risk_transactions) if at_risk_transactions > 0 else 0.0
    revenue_recovery_rate = (recovered_revenue / revenue_at_risk) if revenue_at_risk > 0 else 0.0
    
    # 6. Recovery Costs
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
                total_recovery_cost += 0.50
                
    net_recovered_revenue = recovered_revenue - total_recovery_cost
    roi = ((recovered_revenue - total_recovery_cost) / total_recovery_cost) if total_recovery_cost > 0 else 0.0
    
    # 7. Grouped by Diagnosis Root Cause
    pipeline_cause = [{"$group": {"_id": "$root_cause", "count": {"$sum": 1}}}]
    cause_cursor = db["diagnoses"].aggregate(pipeline_cause)
    cause_distribution = {item["_id"]: item["count"] async for item in cause_cursor}
    
    return {
        "total_transactions": total_transactions,
        "at_risk_transactions": at_risk_transactions,
        "recovered_transactions": recovered_transactions,
        "invalid_recovered_transactions": invalid_recovered_transactions,
        "total_transaction_value": total_transaction_value,
        "total_revenue_at_risk": revenue_at_risk,
        "revenue_at_risk": revenue_at_risk,
        "total_recovered_revenue": recovered_revenue,
        "recovered_revenue": recovered_revenue,
        "normal_success_revenue": normal_success_revenue,
        "net_recovered_revenue": net_recovered_revenue,
        "recovery_rate": transaction_recovery_rate,
        "transaction_recovery_rate": transaction_recovery_rate,
        "revenue_recovery_rate": revenue_recovery_rate,
        "total_recovery_cost": total_recovery_cost,
        "roi": roi,
        "nudge_count": nudge_count,
        "retry_count": retry_count,
        "status_distribution": status_counts,
        "cause_distribution": cause_distribution
    }
