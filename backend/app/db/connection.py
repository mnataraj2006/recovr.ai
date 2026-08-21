import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseConnection:
    client: AsyncIOMotorClient = None
    db = None

    async def connect(self):
        if self.client is None:
            try:
                self.client = AsyncIOMotorClient(settings.MONGO_URI)
                self.db = self.client[settings.MONGO_DB]
                # Ping the database to verify the connection is alive
                await self.client.admin.command('ping')
                logger.info(f"Successfully connected to MongoDB: {settings.MONGO_DB}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB at {settings.MONGO_URI}: {e}")
                raise e

    async def disconnect(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed.")

db_connection = DatabaseConnection()

async def get_db():
    if db_connection.db is None:
        await db_connection.connect()
    return db_connection.db
