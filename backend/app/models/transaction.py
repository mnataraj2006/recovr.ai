from datetime import datetime, timezone
from typing import Optional, Set, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Allowed states in the transaction state machine
TRANSACTION_STATES = {
    "CREATED",
    "CHECKOUT_INITIATED",
    "PAYMENT_ATTEMPTED",
    "CHECKOUT_ABANDONED",
    "SUCCESS",
    "RECOVERED",
    "DIAGNOSING",
    "DIAGNOSED",
    "ACTION_PROPOSED",
    "GUARDRAIL_CHECK",
    "APPROVED",
    "BLOCKED",
    "EXECUTED",
    "RETRY_ESCALATE",
    "UNRECOVERABLE"
}

# State transitions mapping
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    "CREATED": {"CHECKOUT_INITIATED"},
    "CHECKOUT_INITIATED": {"PAYMENT_ATTEMPTED", "CHECKOUT_ABANDONED"},
    "PAYMENT_ATTEMPTED": {"SUCCESS", "DIAGNOSING"},
    "CHECKOUT_ABANDONED": {"DIAGNOSING"},
    "SUCCESS": {"RECOVERED"},
    "DIAGNOSING": {"DIAGNOSED"},
    "DIAGNOSED": {"ACTION_PROPOSED"},
    "ACTION_PROPOSED": {"GUARDRAIL_CHECK"},
    "GUARDRAIL_CHECK": {"APPROVED", "BLOCKED", "UNRECOVERABLE"},
    "APPROVED": {"EXECUTED"},
    "BLOCKED": {"UNRECOVERABLE"},
    "EXECUTED": {"RECOVERED", "RETRY_ESCALATE", "PAYMENT_ATTEMPTED"},
    "RETRY_ESCALATE": {"ACTION_PROPOSED", "UNRECOVERABLE"},
    "RECOVERED": set(),      # Terminal
    "UNRECOVERABLE": set(),  # Terminal
}

def validate_state_transition(current_state: str, new_state: str) -> bool:
    """
    Checks if a transition from current_state to new_state is allowed.
    Allows self-transitions (e.g. updating metadata without changing state).
    """
    if current_state == new_state:
        return True
    if current_state not in VALID_TRANSITIONS:
        return False
    return new_state in VALID_TRANSITIONS[current_state]

class Transaction(BaseModel):
    id: str = Field(..., description="Unique transaction ID starting with 'txn_'")
    checkout_id: str = Field(..., description="Reference ID to Checkout")
    customer_id: str = Field(..., description="Reference ID to Customer")
    amount: float = Field(..., description="Transaction amount in INR")
    status: str = Field(default="CREATED")
    payment_method: Optional[str] = Field(default=None)
    root_cause_id: Optional[str] = Field(default=None, description="Reference ID to Diagnosis")
    last_attempt_id: Optional[str] = Field(default=None, description="Reference ID to last PaymentAttempt")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in TRANSACTION_STATES:
            raise ValueError(f"Invalid transaction state: {v}")
        return v

    def transition_to(self, new_state: str):
        """
        Transitions the transaction to a new state if valid.
        Raises ValueError if the transition is illegal.
        """
        if not validate_state_transition(self.status, new_state):
            raise ValueError(f"Illegal state transition from {self.status} to {new_state}")
        self.status = new_state
        self.updated_at = datetime.now(timezone.utc)
        return self

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "txn_89ab32cde12",
                "checkout_id": "chk_98fa789bcde",
                "customer_id": "cust_82f10b7a",
                "amount": 2999.00,
                "status": "CREATED",
                "payment_method": "upi",
                "root_cause_id": None,
                "last_attempt_id": None,
                "created_at": "2026-08-21T05:00:00Z",
                "updated_at": "2026-08-21T05:00:00Z"
            }
        }
    )
