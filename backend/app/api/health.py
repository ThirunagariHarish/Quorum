from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import engine

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


async def _check_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("health_check_db_failed")
        return False


async def _check_redis() -> bool:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        return True
    except Exception:
        logger.warning("health_check_redis_failed")
        return False


@router.get("/health")
async def health():
    db_ok = await _check_db()
    redis_ok = await _check_redis()

    all_healthy = db_ok and redis_ok
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": {
            "database": db_ok,
            "redis": redis_ok,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
