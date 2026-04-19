import json
import time
from datetime import datetime, timezone

import anthropic
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.core.deps import get_current_user
from backend.app.models.user import User

router = APIRouter(tags=["health"])
logger = structlog.get_logger()

# Haiku model used for the health-check ping — cheapest / fastest
_HEALTH_CHECK_MODEL = "claude-haiku-4-5-20251001"
# Redis key for caching the Claude health result
_REDIS_CACHE_KEY = "health:claude"
_REDIS_CACHE_TTL = 60  # seconds


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


@router.get("/health/claude")
async def check_claude_health(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Test Claude API connectivity with a minimal ping call.

    Results are cached in Redis for 60 seconds to avoid burning tokens on
    repeated monitoring calls.  Requires a valid auth token.

    Returns:
        {
            "status": "ok" | "error" | "not_configured",
            "model": str,
            "latency_ms": float | null,
            "cached": bool,
            "error": str | null,
        }
    """
    # ------------------------------------------------------------------
    # 1. Guard: API key must be configured
    # ------------------------------------------------------------------
    if not settings.ANTHROPIC_API_KEY:
        return {
            "status": "not_configured",
            "model": _HEALTH_CHECK_MODEL,
            "latency_ms": None,
            "cached": False,
            "error": (
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file — see .env.example."
            ),
        }

    # ------------------------------------------------------------------
    # 2. Try to serve from Redis cache
    # ------------------------------------------------------------------
    redis_client = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        cached = await redis_client.get(_REDIS_CACHE_KEY)
        if cached is not None:
            try:
                payload = json.loads(cached)
                payload["cached"] = True
                await redis_client.aclose()
                return payload
            except json.JSONDecodeError:
                # Corrupt cache entry — delete it so it doesn't keep being served
                # for the full TTL. Leave redis_client open so the live-call result
                # can be written back in step 4 below.
                logger.warning("claude_health_redis_cache_corrupt")
                try:
                    await redis_client.delete(_REDIS_CACHE_KEY)
                except Exception:
                    pass
    except Exception as redis_err:
        logger.warning("claude_health_redis_read_failed", error=str(redis_err))
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass
        redis_client = None

    # ------------------------------------------------------------------
    # 3. Real API ping
    # ------------------------------------------------------------------
    result: dict = {
        "status": "ok",
        "model": _HEALTH_CHECK_MODEL,
        "latency_ms": None,
        "cached": False,
        "error": None,
    }

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        t0 = time.monotonic()
        await client.messages.create(
            model=_HEALTH_CHECK_MODEL,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        result["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)

    except anthropic.AuthenticationError as exc:
        result["status"] = "error"
        result["error"] = "Authentication failed — verify ANTHROPIC_API_KEY"
        logger.error("claude_health_auth_error", error=str(exc))

    except anthropic.RateLimitError as exc:
        result["status"] = "error"
        result["error"] = "Anthropic API rate limit reached — try again shortly"
        logger.warning("claude_health_rate_limit", error=str(exc))

    except anthropic.APIStatusError as exc:
        result["status"] = "error"
        result["error"] = f"Anthropic API returned an error (HTTP {exc.status_code})"
        logger.error(
            "claude_health_api_error",
            status_code=exc.status_code,
            error=str(exc),
        )

    except Exception as exc:
        result["status"] = "error"
        result["error"] = "Unexpected error contacting Anthropic API"
        logger.error("claude_health_unexpected_error", error=str(exc))

    # ------------------------------------------------------------------
    # 4. Cache result in Redis (only cache on success to avoid masking
    #    transient errors)
    # ------------------------------------------------------------------
    if result["status"] == "ok":
        try:
            if redis_client is not None:
                await redis_client.set(
                    _REDIS_CACHE_KEY,
                    json.dumps(result),
                    ex=_REDIS_CACHE_TTL,
                )
        except Exception as redis_write_err:
            logger.warning(
                "claude_health_redis_write_failed", error=str(redis_write_err)
            )

    # Close redis connection if still open
    try:
        if redis_client is not None:
            await redis_client.aclose()
    except Exception:
        pass

    return result
