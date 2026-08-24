import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.db.connection import get_db
from app.models.customer import Customer
from app.models.checkout import Checkout, CheckoutItem
from app.models.transaction import Transaction
from app.audit.logger import log_audit_event

router = APIRouter()

class CustomerInput(BaseModel):
    name: str
    email: str
    phone: str

class CheckoutCreateRequest(BaseModel):
    customer: CustomerInput
    cart_value: float
    items: List[CheckoutItem] = Field(default_factory=list)
    device_info: Dict[str, Any] = Field(default_factory=dict)
    simulated_outcomes: Optional[List[str]] = Field(default=None, description="Optional sequence of simulated outcomes")
    customer_response: Optional[str] = Field(default=None, description="Optional customer response preference ('RETURNS' or 'DOES_NOT_RETURN')")

class CheckoutAbandonRequest(BaseModel):
    checkout_duration_seconds: float
    last_viewed_step: Optional[str] = None
    selected_payment_method: Optional[str] = None

@router.post("/checkouts", status_code=status.HTTP_201_CREATED)
async def create_checkout(req: CheckoutCreateRequest, db = Depends(get_db)):
    # 1. Create or Find Customer
    customer_id = f"cust_{uuid.uuid4().hex[:8]}"
    existing_customer = await db["customers"].find_one({"email": req.customer.email})
    if existing_customer:
        customer_id = existing_customer["_id"]
    else:
        new_customer = Customer(
            id=customer_id,
            name=req.customer.name,
            email=req.customer.email,
            phone=req.customer.phone
        )
        doc = new_customer.model_dump()
        doc["_id"] = doc.pop("id")
        await db["customers"].insert_one(doc)

    # 2. Create Checkout Session
    checkout_id = f"chk_{uuid.uuid4().hex[:8]}"
    checkout = Checkout(
        id=checkout_id,
        customer_id=customer_id,
        cart_value=req.cart_value,
        items=req.items,
        device_info=req.device_info,
        status="CHECKOUT_INITIATED"
    )
    chk_doc = checkout.model_dump()
    chk_doc["_id"] = chk_doc.pop("id")
    await db["checkouts"].insert_one(chk_doc)

    # 3. Create Transaction in CREATED state
    transaction_id = f"txn_{uuid.uuid4().hex[:8]}"
    txn = Transaction(
        id=transaction_id,
        checkout_id=checkout_id,
        customer_id=customer_id,
        amount=req.cart_value,
        status="CREATED",
        simulated_outcomes=req.simulated_outcomes
    )

    # Transition to CHECKOUT_INITIATED
    txn.transition_to("CHECKOUT_INITIATED")
    
    txn_doc = txn.model_dump()
    txn_doc["_id"] = txn_doc.pop("id")
    if req.customer_response:
        txn_doc["customer_response"] = req.customer_response
    await db["transactions"].insert_one(txn_doc)

    # 4. Log Audit Event
    await log_audit_event(
        transaction_id=transaction_id,
        event_type="CHECKOUT_CREATED",
        actor="CUSTOMER",
        source="CheckoutsAPI",
        reason="Customer initiated checkout flow and filled items details.",
        metadata={"cart_value": req.cart_value, "items_count": len(req.items)}
    )

    return {
        "success": True,
        "checkout_id": checkout_id,
        "transaction_id": transaction_id,
        "status": txn.status
    }

@router.post("/checkouts/{checkout_id}/abandon")
async def abandon_checkout(checkout_id: str, req: CheckoutAbandonRequest, db = Depends(get_db)):
    # 1. Fetch checkout
    checkout_doc = await db["checkouts"].find_one({"_id": checkout_id})
    if not checkout_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkout {checkout_id} not found."
        )

    # Update Checkout session status
    await db["checkouts"].update_one(
        {"_id": checkout_id},
        {"$set": {
            "status": "CHECKOUT_ABANDONED",
            "checkout_duration_seconds": req.checkout_duration_seconds
        }}
    )

    # 2. Fetch linked Transaction
    txn_doc = await db["transactions"].find_one({"checkout_id": checkout_id})
    if not txn_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transaction linked to checkout {checkout_id} found."
        )

    txn_doc["id"] = txn_doc.pop("_id")
    txn = Transaction(**txn_doc)

    # Check state and transition: -> CHECKOUT_ABANDONED -> DIAGNOSING
    try:
        txn.transition_to("CHECKOUT_ABANDONED")
        txn.transition_to("DIAGNOSING")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    txn_data = txn.model_dump()
    txn_data["_id"] = txn_data.pop("id")
    await db["transactions"].replace_one({"_id": txn.id}, txn_data)

    # Trigger Recovery Service in background
    from app.services.recovery_service import recovery_service
    import asyncio
    task = asyncio.create_task(
        recovery_service.process_checkout_abandonment(
            txn.id,
            fast_mode=True
        )
    )
    recovery_service.track_task(task)

    # 3. Log Audit Event
    await log_audit_event(
        transaction_id=txn.id,
        event_type="CHECKOUT_ABANDONED",
        actor="CUSTOMER",
        source="CheckoutsAPI",
        reason="Checkout session abandoned by customer before starting payment.",
        metadata={
            "checkout_duration_seconds": req.checkout_duration_seconds,
            "last_viewed_step": req.last_viewed_step,
            "selected_payment_method": req.selected_payment_method
        }
    )

    return {
        "success": True,
        "transaction_id": txn.id,
        "status": txn.status
    }

@router.get("/transactions/{id}")
async def get_transaction(id: str, db = Depends(get_db)):
    txn_doc = await db["transactions"].find_one({"_id": id})
    if not txn_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {id} not found."
        )
    
    txn_doc["id"] = txn_doc.pop("_id")
    customer_doc = await db["customers"].find_one({"_id": txn_doc["customer_id"]})
    attempts_count = await db["payment_attempts"].count_documents({"transaction_id": id})

    return {
        "transaction": txn_doc,
        "customer": customer_doc,
        "payment_attempts_count": attempts_count
    }

@router.get("/transactions")
async def list_transactions(status: Optional[str] = None, limit: int = 20, offset: int = 0, db = Depends(get_db)):
    query = {}
    if status:
        query["status"] = status
    
    cursor = db["transactions"].find(query).sort("created_at", -1).skip(offset).limit(limit)
    transactions = []
    async for doc in cursor:
        doc["id"] = doc.pop("_id")
        
        # Inline lookup for customer details
        cust = await db["customers"].find_one({"_id": doc["customer_id"]})
        if cust:
            doc["customer_name"] = cust["name"]
            doc["customer_email"] = cust["email"]
            doc["customer_phone"] = cust["phone"]
        else:
            doc["customer_name"] = "Unknown Customer"
            doc["customer_email"] = ""
            doc["customer_phone"] = ""
            
        transactions.append(doc)
        
    total = await db["transactions"].count_documents(query)
    return {
        "transactions": transactions,
        "total": total
    }
