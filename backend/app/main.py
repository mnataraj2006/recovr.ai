import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.db.connection import db_connection, get_db
from app.services.auth_service import ensure_seed_user
from app.middleware import SecurityMiddleware

from app.api.routes import checkouts, payments, recovery, metrics, audit, simulation, auth, api_keys, health

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB Client connection & seed admin user
    logger.info(f"Starting up Recovr.ai Backend (Environment: {settings.ENVIRONMENT})...")
    try:
        await db_connection.connect()
        db = await get_db()
        await ensure_seed_user(db)
    except Exception as e:
        logger.critical(f"Startup DB connection failed: {e}")
        if settings.ENVIRONMENT.lower() == "production":
            raise e
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

# Custom security middleware (request correlation ID & sliding-window rate limiting)
app.add_middleware(SecurityMiddleware)

# CORS configuration based on environment settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register routers under v1 API
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(api_keys.router, prefix="/api/v1", tags=["API Keys"])
app.include_router(checkouts.router, prefix="/api/v1", tags=["Checkouts"])
app.include_router(payments.router, prefix="/api/v1", tags=["Payments"])
app.include_router(recovery.router, prefix="/api/v1", tags=["Recovery"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
app.include_router(simulation.router, prefix="/api/v1", tags=["Simulation"])

# Serve static frontend files if built
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
