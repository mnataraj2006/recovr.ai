import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.db.connection import db_connection, get_db

from app.api.routes import checkouts, payments, recovery, metrics, audit, simulation

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

# Allow the Vite dev server (and any localhost port) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under v1 API
app.include_router(checkouts.router, prefix="/api/v1", tags=["Checkouts"])
app.include_router(payments.router, prefix="/api/v1", tags=["Payments"])
app.include_router(recovery.router, prefix="/api/v1", tags=["Recovery"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
app.include_router(simulation.router, prefix="/api/v1", tags=["Simulation"])

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

# Serve static frontend files if built
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
