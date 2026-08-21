from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class Customer(BaseModel):
    id: str = Field(..., description="Unique customer ID starting with 'cust_'")
    name: str
    email: str
    phone: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "cust_82f10b7a",
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "phone": "+919876543210",
                "created_at": "2026-08-21T05:00:00Z"
            }
        }
    )
