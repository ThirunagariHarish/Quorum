# Phase 2 — Claude API Audit + Health Check Endpoint
## Implementation Notes

**Date:** 2025-Q3  
**Engineer:** Devin  

---

## Summary of Changes

### Background
The user asked whether PaperPilot agents use the Claude API or the Claude Max consumer subscription. Research confirmed:
- The project already correctly uses `anthropic.AsyncAnthropic()` (standard Anthropic Python SDK / paid API).
- **Claude Max** is a consumer subscription at claude.ai and has **no API access** — it is unrelated to this project.
- One model ID was incorrect and would have caused all "simple" tier calls to fail with a 404/invalid-model error.

---

## Files Changed

| File | Change Type | Description |
|---|---|---|
| `agents/token_engine/router.py` | Fix + Enhancement | Corrected Haiku model ID; added `MAX_CONTEXT_TOKENS`; added `get_all_models()`; improved inline docs |
| `agents/token_engine/engine.py` | Enhancement | Added `try/except` around `client.messages.create()`; fixed `_tier_from_model` reverse map |
| `backend/app/api/health.py` | Feature | Added `GET /health/claude` endpoint with Redis caching, auth guard, and latency reporting |
| `backend/app/main.py` | Fix | Fixed seeded Blog Reviewer default model ID |
| `.env.example` | Documentation | Fully documented all environment variables |

---

## Task 2.1 — Model ID Audit Results

**Source:** `https://docs.anthropic.com/en/docs/about-claude/models/overview` (fetched live)

| Tier | Old ID | New ID | Valid? |
|---|---|---|---|
| deep | `claude-opus-4-20250514` | `claude-opus-4-20250514` | ✅ No change needed |
| standard | `claude-sonnet-4-20250514` | `claude-sonnet-4-20250514` | ✅ No change needed |
| simple | `claude-haiku-4-20250514` | `claude-haiku-4-5-20251001` | ❌ **Was wrong — fixed** |

**Key finding:** `claude-haiku-4-20250514` does **not** exist in Anthropic's model catalog.  
The correct Claude 4 Haiku model ID is `claude-haiku-4-5-20251001`.  
The old ID would have caused all `simple` tier calls and budget-downgrade calls to receive an API 404 error.

### Pricing (confirmed unchanged)
| Model | Input ($/MTok) | Output ($/MTok) |
|---|---|---|
| claude-opus-4-20250514 | $5.00 | $25.00 |
| claude-sonnet-4-20250514 | $3.00 | $15.00 |
| claude-haiku-4-5-20251001 | $1.00 | $5.00 |

---

## Task 2.2 — `/health/claude` Endpoint

**Route:** `GET /api/v1/health/claude`  
**Auth:** Required (Bearer token via `get_current_user`)

### Behaviour
1. Returns `{"status": "not_configured"}` immediately if `ANTHROPIC_API_KEY` is blank.
2. Checks Redis cache (`health:claude`, TTL=60s) — returns cached result with `"cached": true` on hit.
3. On cache miss: makes a minimal API call (`max_tokens=1`, prompt `"ping"`) to `claude-haiku-4-5-20251001` and measures latency.
4. Caches successful results in Redis for 60 seconds.
5. Returns structured JSON: `{status, model, latency_ms, cached, error}`.

### Error handling coverage
- `anthropic.AuthenticationError` → status "error", descriptive message
- `anthropic.RateLimitError` → status "error", logged as warning
- `anthropic.APIStatusError` → status "error", includes HTTP status code
- All other exceptions → status "error", generic message

---

## Task 2.3 — `get_all_models()` in `ModelRouter`

Added as a `@staticmethod`:
```python
@staticmethod
def get_all_models() -> list[str]:
    """Return a deduplicated list of all configured model IDs."""
    return list(set(TIER_TO_MODEL.values()))
```
Also added `MAX_CONTEXT_TOKENS` constant dict for future prompt-size checks.

---

## Task 2.4 — `.env.example` Documentation

All environment variables from `backend/app/core/config.py` are now documented:
- `DATABASE_URL` — format + purpose
- `REDIS_URL` — purpose
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_SECURE`
- `JWT_SECRET` — generation command included
- `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- `ENCRYPTION_KEY` — generation command included
- `ANTHROPIC_API_KEY` — explicit note that Claude Max ≠ API access; model tier table included
- `CORS_ORIGINS` — JSON array format note

---

## Task 2.5 — Error Handling in `engine.py`

Wrapped `client.messages.create(**kwargs)` with:
- `anthropic.AuthenticationError` → raises `ValueError` with actionable message
- `anthropic.RateLimitError` → logs warning, re-raises
- `anthropic.APIStatusError` → logs error with status code + message, re-raises
- `Exception` (catch-all) → logs error, re-raises

All log entries include `agent_type` and `task_phase` in `extra` dict for structured logging.

---

## Compile Check

```
python3 -m py_compile \
    backend/app/api/health.py \
    agents/token_engine/engine.py \
    agents/token_engine/router.py \
    backend/app/main.py
# → ✅ All files compile successfully
```

---

## Deviations from Plan

None. All tasks implemented as specified.

---

## Open Risks

1. **Newer model versions available:** Anthropic now has `claude-opus-4-5-20251101`, `claude-sonnet-4-5-20250929`, etc. The project uses the `..-20250514` GA versions, which are still valid. Consider upgrading in a future phase if newer capabilities are needed.
2. **Redis unavailability:** If Redis is down, the Claude health check will still make the live API call (no caching) and log a warning — this is intentional graceful degradation.
3. **`logger.warning(...)` with `extra=` kwarg:** The `logging` module's `warning`/`error` methods accept `extra` as a keyword argument, but only some handlers surface it. If structlog replaces the root logger in future, the call signature should be verified.
