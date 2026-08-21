from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class CheckoutItem(BaseModel):
    sku: str
    name: str
    price: float
    quantity: int

class Checkout(BaseModel):
    id: str = Field(..., description="Unique checkout ID starting with 'chk_'")
    customer_id: str = Field(..., description="Reference ID to Customer")
    cart_value: float = Field(..., description="Total checkout cart value in INR")
    items: List[CheckoutItem] = Field(default_factory=list)
    checkout_duration_seconds: Optional[float] = Field(default=0.0)
    device_info: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="CHECKOUT_INITIATED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "chk_98fa789bcde",
                "customer_id": "cust_82f10b7a",
                "cart_value": 2999.00,
                "items": [
                    {
                        "sku": "SKU-PREMIUM-SUB",
                        "name": "Recovr Annual Plan",
                        "price": 2999.00,
                        "quantity": 1
                    }
                ],
                "checkout_duration_seconds": 45.2,
                "device_info": {
                  "ip": "192.168.1.1",
                  "user_agent": "Mozilla/5.0...",
                  "platform": "Android"
                },
                "status": "CHECKOUT_INITIATED",
                "created_at": "2026-08-21T05:00:00Z"
            }
        }
    )
