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
    
    # 2. Total Revenue at Risk (Sum of all checkouts/transactions)
    pipeline_risk = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    risk_cursor = db["transactions"].aggregate(pipeline_risk)
    risk_result = await risk_cursor.to_list(length=1)
    total_revenue_at_risk = risk_result[0]["total"] if risk_result else 0.0
    
    # 3. Total Recovered Revenue (Transactions in RECOVERED or SUCCESS state)
    pipeline_recovered = [
        {"$match": {"status": {"$in": ["RECOVERED", "SUCCESS"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    recovered_cursor = db["transactions"].aggregate(pipeline_recovered)
    recovered_result = await recovered_cursor.to_list(length=1)
    total_recovered_revenue = recovered_result[0]["total"] if recovered_result else 0.0
    
    # 4. Recovery Rate
    recovery_rate = (total_recovered_revenue / total_revenue_at_risk) if total_revenue_at_risk > 0 else 0.0
    
    # 5. Recovery Costs
    # SMS/WhatsApp = ₹0.50, API Retries = ₹1.00
    nudge_count = await db["recovery_actions"].count_documents({"action_type": "NUDGE_CUSTOMER"})
    retry_count = await db["recovery_actions"].count_documents({"action_type": "RETRY_PAYMENT"})
    
    total_recovery_cost = (nudge_count * 0.50) + (retry_count * 1.00)
    net_recovered_revenue = total_recovered_revenue - total_recovery_cost
    
    # 6. Return ROI
    roi = (total_recovered_revenue / total_recovery_cost) if total_recovery_cost > 0 else 0.0
    
    # 7. Grouped by Diagnosis Root Cause
    pipeline_cause = [{"$group": {"_id": "$root_cause", "count": {"$sum": 1}}}]
    cause_cursor = db["diagnoses"].aggregate(pipeline_cause)
    cause_distribution = {item["_id"]: item["count"] async for item in cause_cursor}
    
    return {
        "total_revenue_at_risk": total_revenue_at_risk,
        "total_recovered_revenue": total_recovered_revenue,
        "net_recovered_revenue": net_recovered_revenue,
        "recovery_rate": recovery_rate,
        "total_recovery_cost": total_recovery_cost,
        "roi": roi,
        "nudge_count": nudge_count,
        "retry_count": retry_count,
        "status_distribution": status_counts,
        "cause_distribution": cause_distribution
    }
