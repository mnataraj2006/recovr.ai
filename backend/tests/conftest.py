import pytest
import asyncio
import pytest_asyncio
from app.config.settings import settings
from app.db.connection import db_connection

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def db():
    """Initialize test database client and drop database on tear-down."""
    # Force settings to target a clean test database
    settings.MONGO_DB = "recovr_test_db"
    
    # Reset client connection to bind to the current event loop
    await db_connection.disconnect()
    await db_connection.connect()
    yield db_connection.db
    
    if db_connection.client is not None:
        # Clean up database records
        await db_connection.client.drop_database("recovr_test_db")
        await db_connection.disconnect()
