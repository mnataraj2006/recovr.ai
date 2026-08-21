import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.config.settings import settings
from app.db.connection import db_connection, get_db

from app.api.routes import checkouts, payments, recovery

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB Client connection
    logger.info("Starting up Recovr.ai Backend...")
    try:
        await db_connection.connect()
    except Exception as e:
        logger.critical(f"Startup DB connection failed: {e}")
    yield
    # Shutdown: Close database connection pool
    logger.info("Shutting down Recovr.ai Backend...")
    await db_connection.disconnect()

app = FastAPI(
    title="Recovr.ai",
    description="AI-powered checkout and payment recovery system.",
    version="1.0.0",
    lifespan=lifespan
)

# Register routers under v1 API
app.include_router(checkouts.router, prefix="/api/v1", tags=["Checkouts"])
app.include_router(payments.router, prefix="/api/v1", tags=["Payments"])
app.include_router(recovery.router, prefix="/api/v1", tags=["Recovery"])

@app.get("/health")
async def health_check(db = Depends(get_db)):
    try:
        # Ping the DB as a health check
        await db.client.admin.command('ping')
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Health check database ping failed: {e}")
        db_status = f"unhealthy ({str(e)})"

    return {
        "status": "online",
        "environment": settings.ENVIRONMENT,
        "database": db_status
    }
