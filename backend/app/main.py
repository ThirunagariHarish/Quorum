from __future__ import annotations

from typing import Optional

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.core.security import verify_token
from backend.app.models import Base
from backend.app.models.agent import Agent

from backend.app.api.auth import router as auth_router
from backend.app.api.papers import router as papers_router
from backend.app.api.latex import router as latex_router
from backend.app.api.agents import router as agents_router
from backend.app.api.tasks import router as tasks_router
from backend.app.api.reviews import router as reviews_router
from backend.app.api.tokens import router as tokens_router
from backend.app.api.settings import router as settings_router
from backend.app.api.deadlines import router as deadlines_router
from backend.app.api.publishing import router as publishing_router
from backend.app.api.scheduler import router as scheduler_router
from backend.app.api.health import router as health_router

from backend.app.services.storage import storage_service
from backend.app.services.scheduler import scheduler_service
from backend.app.ws.manager import ws_manager

logger = structlog.get_logger()

DEFAULT_AGENTS = [
    {"name": "Research Orchestrator", "agent_type": "orchestrator", "default_model": "claude-sonnet-4-20250514"},
    {"name": "IEEE Research Agent", "agent_type": "ieee", "default_model": "claude-opus-4-20250514"},
    {"name": "Small Paper Agent", "agent_type": "small_paper", "default_model": "claude-sonnet-4-20250514"},
    {"name": "Blog Agent", "agent_type": "blog", "default_model": "claude-sonnet-4-20250514"},
    {"name": "IEEE Reviewer", "agent_type": "reviewer_ieee", "default_model": "claude-opus-4-20250514"},
    {"name": "Small Paper Reviewer", "agent_type": "reviewer_small", "default_model": "claude-sonnet-4-20250514"},
    {"name": "Blog Reviewer", "agent_type": "reviewer_blog", "default_model": "claude-haiku-4-5-20251001"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup_begin")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    # Init MinIO buckets
    try:
        storage_service.init_buckets()
        logger.info("minio_buckets_initialized")
    except Exception as e:
        logger.warning("minio_init_failed", error=str(e))

    # Seed default agents
    from backend.app.core.database import async_session_factory
    async with async_session_factory() as session:
        for agent_data in DEFAULT_AGENTS:
            result = await session.execute(
                select(Agent).where(Agent.name == agent_data["name"])
            )
            if result.scalar_one_or_none() is None:
                session.add(Agent(**agent_data))
                logger.info("agent_seeded", name=agent_data["name"])
        await session.commit()
    logger.info("agents_seed_complete")

    # Start scheduler
    scheduler_service.start()

    # Start WebSocket pub/sub listener
    pubsub_task = asyncio.create_task(ws_manager.start_pubsub())

    logger.info("startup_complete")
    yield

    # Shutdown
    logger.info("shutdown_begin")
    pubsub_task.cancel()
    try:
        await pubsub_task
    except asyncio.CancelledError:
        pass
    scheduler_service.shutdown()
    await ws_manager.shutdown()
    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="Quorum API",
    description="Autonomous multi-agent research platform API",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers under /api/v1
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(papers_router, prefix=API_PREFIX)
app.include_router(latex_router, prefix=API_PREFIX)
app.include_router(agents_router, prefix=API_PREFIX)
app.include_router(tasks_router, prefix=API_PREFIX)
app.include_router(reviews_router, prefix=API_PREFIX)
app.include_router(tokens_router, prefix=API_PREFIX)
app.include_router(settings_router, prefix=API_PREFIX)
app.include_router(deadlines_router, prefix=API_PREFIX)
app.include_router(publishing_router, prefix=API_PREFIX)
app.include_router(scheduler_router, prefix=API_PREFIX)
app.include_router(health_router, prefix=API_PREFIX)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    payload = verify_token(token, expected_type="access")
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Client messages can be handled here (e.g., ping/pong)
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
