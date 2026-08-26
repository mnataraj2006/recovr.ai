from fastapi import APIRouter, Depends, HTTPException, status
from app.db.connection import get_db
from app.simulation.runner import simulation_runner

router = APIRouter()

@router.post("/simulation/run", status_code=status.HTTP_201_CREATED)
async def run_simulation(db = Depends(get_db)):
    """
    Executes a new cohort batch simulation.
    Runs 5 synthetic checkouts with timeout failures, declines, and abandonments,
    and returns the recovery summary analytics.
    """
    try:
        report = await simulation_runner.run_batch_cohort()
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation run failed: {str(e)}"
        )

@router.get("/simulation/history")
async def get_simulation_history(db = Depends(get_db)):
    """
    Retrieves all past simulation reports in reverse chronological order.
    """
    cursor = db["simulation_cohorts"].find({}).sort("created_at", -1)
    history = await cursor.to_list(length=100)
    for item in history:
        item["id"] = item.pop("_id")
    return history

@router.delete("/simulation/clear")
async def clear_simulation_data(db = Depends(get_db)):
    """
    Clears all simulation cohorts, test transactions, checkouts, payments,
    audits, and recovery metrics to start with a fresh clean state for Postman/Live testing.
    """
    collections = [
        "simulation_cohorts",
        "checkouts",
        "transactions",
        "payments",
        "payment_attempts",
        "diagnoses",
        "recovery_actions",
        "guardrail_decisions",
        "audit_events",
        "recovery_outcomes",
    ]
    for col in collections:
        await db[col].delete_many({})
        
    return {
        "success": True,
        "message": "All simulation cohort data and test transactions cleared successfully."
    }

