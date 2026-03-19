"""FastAPI application entry point.

Startup sequence:
  1. Create DB tables (idempotent).
  2. Launch campaign worker and timeout scheduler as asyncio background tasks.

Shutdown sequence:
  1. Signal background tasks to stop.
  2. Cancel and await their asyncio tasks.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.database.engine import create_tables
from app.middleware.security import SecurityHeadersMiddleware
from app.workers.campaign_worker import get_worker
from app.workers.scheduler import get_scheduler

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    logger.info("Database tables ready")

    worker = get_worker()
    scheduler = get_scheduler()

    worker_task = asyncio.create_task(worker.start(), name="campaign-worker")
    scheduler_task = asyncio.create_task(scheduler.start(), name="timeout-scheduler")
    logger.info("Background tasks started")

    yield

    worker.stop()
    scheduler.stop()
    worker_task.cancel()
    scheduler_task.cancel()
    logger.info("Background tasks stopped")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=[settings.api_key_header, "Content-Type"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix="/api")

@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness probe — returns 200 when the service is running."""
    return {"status": "ok", "service": settings.app_name}
