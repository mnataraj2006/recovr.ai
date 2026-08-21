from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class AuditEvent(BaseModel):
    id: str = Field(..., description="Unique audit event ID starting with 'aud_'")
    transaction_id: str = Field(..., description="Reference ID to Transaction")
    event_type: str = Field(..., description="Type of event (e.g., CHECKOUT_CREATED, PAYMENT_FAILED)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = Field(..., description="Entity that initiated the action: SYSTEM, AGENT, USER, CUSTOMER")
    source: str = Field(..., description="System component that generated the log")
    reason: str = Field(..., description="Human-readable description of why this event occurred")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual payload metadata")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "aud_12345678",
                "transaction_id": "txn_89ab32cde12",
                "event_type": "CHECKOUT_CREATED",
                "timestamp": "2026-08-21T05:00:00Z",
                "actor": "CUSTOMER",
                "source": "WebhookHandler",
                "reason": "Customer initiated checkout flow",
                "metadata": { "cart_value": 2999.00 }
            }
        }
    )
