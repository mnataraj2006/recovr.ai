from fastapi import APIRouter, Depends, HTTPException, status
from app.db.connection import get_db
from app.simulation.runner import simulation_runner
from app.config.settings import settings
from app.api.dependencies import require_role
from app.audit.logger import log_audit_event

router = APIRouter()

@router.post("/simulation/run", status_code=status.HTTP_201_CREATED)
async def run_simulation(
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN", "OPERATOR"]))
):
    """
    Executes a new cohort batch simulation.
    Runs 5 synthetic checkouts with timeout failures, declines, and abandonments,
    and returns the recovery summary analytics.
    """
    try:
        report = await simulation_runner.run_batch_cohort()
        await log_audit_event(
            transaction_id="SIMULATION",
            event_type="SIMULATION_RUN_EXECUTED",
            actor="USER",
            source="SimulationRouter",
            reason=f"Cohort batch simulation executed by user {current_user['email']}.",
            metadata={"run_by": current_user["email"]}
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation run failed: {str(e)}"
        )

from app.api.dependencies import require_role, get_current_user

@router.get("/simulation/history")
async def get_simulation_history(
    db = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves all past simulation reports in reverse chronological order.
    """
    cursor = db["simulation_cohorts"].find({}).sort("created_at", -1)
    history = await cursor.to_list(length=100)
    for item in history:
        item["id"] = str(item.pop("_id"))
    return history

@router.delete("/simulation/clear")
async def clear_simulation_data(
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    """
    Clears all simulation cohorts, test transactions, checkouts, payments,
    audits, and recovery metrics to start with a fresh clean state for Postman/Live testing.
    STRICTLY BLOCKED IN PRODUCTION.
    """
    if settings.ENVIRONMENT.lower() == "production":
        await log_audit_event(
            transaction_id="SECURITY",
            event_type="SIMULATION_CLEAR_BLOCKED",
            actor="USER",
            source="SimulationRouter",
            reason=f"Blocked attempt to clear simulation data in production by {current_user['email']}.",
            metadata={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation dataset clearing is strictly disabled in production environments."
        )

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

    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="SIMULATION_DATA_CLEARED",
        actor="USER",
        source="SimulationRouter",
        reason=f"All test simulation cohort and transaction records cleared by admin {current_user['email']}.",
        metadata={"cleared_by": current_user["email"]}
    )

    return {
        "success": True,
        "message": "All simulation cohort data and test transactions cleared successfully."
    }
