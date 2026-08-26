import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseConnection:
    client: AsyncIOMotorClient = None
    loop = None

    async def create_indexes(self):
        """Creates required performance and uniqueness indexes."""
        db = self.client[settings.MONGO_DB]
        try:
            # Unique indexes
            await db["users"].create_index("email", unique=True)
            await db["api_keys"].create_index("key_hash", unique=True)
            await db["webhook_events"].create_index("event_id", unique=True)

            # Performance indexes
            await db["api_keys"].create_index("prefix")
            await db["transactions"].create_index("checkout_id")
            await db["transactions"].create_index("status")
            await db["transactions"].create_index("created_at")
            await db["payment_attempts"].create_index([("transaction_id", 1), ("status", 1)])
            await db["audit_events"].create_index([("transaction_id", 1), ("timestamp", -1)])
            logger.info("MongoDB database indexes ensured successfully.")
        except Exception as e:
            logger.warning(f"Error creating database indexes: {e}")

    async def connect(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
            
        if self.client is None:
            try:
                self.client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
                # Ping the database to verify the connection is alive
                await self.client.admin.command('ping')
                await self.create_indexes()
                logger.info(f"Successfully connected to MongoDB client (loop: {id(self.loop)})")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB at {settings.MONGO_URI}: {e}")
                if settings.ENVIRONMENT.lower() == "production":
                    raise RuntimeError(f"CRITICAL: Production MongoDB startup failed: {e}")
                raise e

    async def disconnect(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.loop = None
            logger.info("MongoDB connection closed.")

db_connection = DatabaseConnection()

async def get_db():
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None
        
    # Reconnect if client is not connected, or if event loop has changed
    if db_connection.client is None or db_connection.loop != current_loop:
        if db_connection.client is not None:
            db_connection.client.close()
            db_connection.client = None
        await db_connection.connect()
        
    # Dynamically resolve database based on current settings
    return db_connection.client[settings.MONGO_DB]

