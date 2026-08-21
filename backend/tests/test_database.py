import pytest
from datetime import datetime
from app.models.customer import Customer
from app.models.checkout import Checkout, CheckoutItem

@pytest.mark.asyncio
async def test_mongodb_connection_ping(db):
    """Test that we can ping the database client."""
    response = await db.client.admin.command("ping")
    assert response.get("ok") == 1.0

@pytest.mark.asyncio
async def test_customer_crud_operations(db):
    """Test creating, reading, and deleting a Customer document."""
    # 1. Create Customer Pydantic model instance
    customer_data = Customer(
        id="cust_test123",
        name="John Test",
        email="john.test@example.com",
        phone="+919999988888"
    )

    # 2. Insert into MongoDB collection with mapped primary key
    doc = customer_data.model_dump()
    doc["_id"] = doc.pop("id")
    collection = db["customers"]
    insert_result = await collection.insert_one(doc)
    assert insert_result.inserted_id == "cust_test123"

    # 3. Read back from database
    found_doc = await collection.find_one({"_id": "cust_test123"})
    assert found_doc is not None
    assert found_doc["name"] == "John Test"
    assert found_doc["email"] == "john.test@example.com"

    # 4. Clean up
    delete_result = await collection.delete_one({"_id": "cust_test123"})
    assert delete_result.deleted_count == 1
    
    # Verify deletion
    deleted_doc = await collection.find_one({"_id": "cust_test123"})
    assert deleted_doc is None

@pytest.mark.asyncio
async def test_checkout_relationships(db):
    """Test inserting a Checkout referencing a Customer."""
    checkout_data = Checkout(
        id="chk_test123",
        customer_id="cust_test123",
        cart_value=1500.0,
        items=[
            CheckoutItem(sku="SKU-1", name="Test Item", price=1500.0, quantity=1)
        ],
        checkout_duration_seconds=30.0,
        device_info={"platform": "Desktop"},
        status="CHECKOUT_INITIATED"
    )

    doc = checkout_data.model_dump()
    doc["_id"] = doc.pop("id")
    collection = db["checkouts"]
    insert_result = await collection.insert_one(doc)
    assert insert_result.inserted_id == "chk_test123"

    # Find checkout
    checkout_doc = await collection.find_one({"_id": "chk_test123"})
    assert checkout_doc is not None
    assert checkout_doc["cart_value"] == 1500.0
    assert len(checkout_doc["items"]) == 1
    assert checkout_doc["items"][0]["sku"] == "SKU-1"

    # Clean up
    await collection.delete_one({"_id": "chk_test123"})
