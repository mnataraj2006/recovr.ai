import pytest
import asyncio
import pytest_asyncio
import uuid
from app.config.settings import settings
from app.db.connection import get_db, db_connection

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def session_db():
    """Initialize database client connection once for the entire test session."""
    await db_connection.disconnect()
    await db_connection.connect()
    yield
    await db_connection.disconnect()

def get_admin_headers():
    from app.services.auth_service import create_access_token
    token = create_access_token({"sub": "usr_seed_admin", "email": "admin@recovr.ai", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers():
    return get_admin_headers()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def db():
    """Initialize unique test database client and drop database on tear-down."""
    test_db_name = f"recovr_test_db_{uuid.uuid4().hex[:8]}"
    settings.MONGO_DB = test_db_name
    
    # Retrieve DB instance (dynamically resolves to unique DB name)
    database = await get_db()
    
    from app.services.auth_service import ensure_seed_user
    await ensure_seed_user(database)
    
    yield database
    
    # Wait for all background tasks to complete before tearing down database
    from app.services.recovery_service import recovery_service
    await recovery_service.wait_for_pending_tasks()
    
    # Drop this test function's unique database
    if db_connection.client is not None:
        try:
            await db_connection.client.drop_database(test_db_name)
        except Exception:
            pass
