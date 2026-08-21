import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseConnection:
    client: AsyncIOMotorClient = None
    loop = None

    async def connect(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
            
        if self.client is None:
            try:
                self.client = AsyncIOMotorClient(settings.MONGO_URI)
                # Ping the database to verify the connection is alive
                await self.client.admin.command('ping')
                logger.info(f"Successfully connected to MongoDB client (loop: {id(self.loop)})")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB at {settings.MONGO_URI}: {e}")
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
