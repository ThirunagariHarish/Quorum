# Changelog

All notable changes to PaperPilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.3.0] — 2026-04-19

### Security
- **P0** Remove hardcoded defaults for `JWT_SECRET` and `ENCRYPTION_KEY` — app now refuses to start if either is unset
- **P0** Strict 32-byte `ENCRYPTION_KEY` validation replaces silent truncation/padding
- **Fix** 6× IDOR vulnerabilities in `reviews.py` — all endpoints now JOIN Paper and filter by authenticated user_id
- **Fix** `sort_by` SQL injection surface in `papers.py` replaced with `ALLOWED_SORT_COLS` allowlist

### Bug Fixes

**Auth**
- `/auth/refresh` now returns 401 (not 500) on malformed/non-UUID tokens
- Password field enforces min 8 / max 128 characters

**Token Engine**
- Float epsilon fix: budget thresholds use `< (X - 1e-9)` to avoid IEEE 754 false CRITICAL triggers at exactly 90% spend
- `granularity` query param now drives `date_trunc` correctly; returns 400 on invalid values
- `get_budget()` checks both daily and monthly limits, returning worst severity
- Symmetric 7-day trend windows (both current and previous week are 7 days inclusive)
- `projected_monthly` uses `calendar.monthrange` for accurate days-remaining calculation

**Paper Generation**
- `IEEE_SYSTEM_PROMPT` is now passed to all 4 LLM calls in `ieee/agent.py` (was imported but never used)
- `spawn_scouts` and `spawn_researchers` parallelized with `asyncio.gather`
- `RuntimeError` raised when all scouts or all researchers fail (was silently returning empty paper)
- Agent task assignment (`agents.py`) is now atomic: `.with_for_update()` + status set to `"active"` in same transaction

**LaTeX**
- `parse_errors` regex no longer matches across newlines (prevented false error detection)
- `attempt_auto_fix()` is called as one-shot retry inside `compile()`
- `_ensure_balance()` rewritten to detect and reposition misplaced `\balance` commands

**Storage / MinIO**
- All 5 async methods in `storage.py` wrapped with `asyncio.to_thread` (were blocking event loop)
- DELETE handler in `papers.py` uses `asyncio.to_thread` for MinIO object iteration

**Health**
- Redis corrupt-cache healing: evict stale key, keep connection open for write-back

**Frontend**
- `compilePaper()` moved into `ApiClient` with correct JSON field names (`tex_content`, `bib_content`, `pdf_b64`) and Bearer token — was broken in 3 independent ways
- `getReviews`, `getReviewComments`, `getDeadlines` return types corrected to bare arrays
- `review/page.tsx`: `handleSelect` now fetches real `reviewId` via `api.getPaper()`
- `review/page.tsx`: reviews sorted by `created_at` desc before selecting active review
- `deadlines/page.tsx`: async IIFE + cancelled guard prevents stale setState on unmount
- `use-websocket.ts`: `onerror` handler added; exponential backoff reconnect (1s→16s, max 5 attempts); ghost-connection leak on unmount fixed with `alive` flag
- `review-store.ts`: `getReviewComments` consumer updated to `Comment[]` direct return
- `pdf-preview.tsx`: `sandbox="allow-same-origin"` (was empty string — broke PDF rendering); single URL revocation point
- `ws/manager.py`: `asyncio.Optional[Task]` → `Optional[asyncio.Task]` import fix

**Infrastructure**
- `docker-compose.yml`: `ENCRYPTION_KEY` updated to exactly 32-byte value
- `.env.example`: documents all required env vars with generation instructions

### Changed
- `frontend` package version bumped `0.2.0 → 0.3.0`
- FastAPI app version bumped `1.1.0 → 1.2.0`

### Known Issues (deferred to next release)
- `backend/tests/` is empty — no automated test coverage; all QA was static analysis
- Telegram test button non-functional (BUG-008, P2)
- Files page eye button is a no-op (BUG-010, P2)
- Scheduler `_run_orchestrator()` is a stub (P2)
- WebSocket token in URL query string (architectural debt, tracked)

---

## [0.2.0] — 2025-07-14

### Fixed
- IEEE paper text overlaps eliminated — added `microtype`, `\balance`, `\sloppy`/`\emergencystretch` to both `ieee_conference.tex` and `ieee_short.tex`
- Equations now correctly wrapped in LaTeX math environments via `pre_process()` pipeline in `LaTeXCompiler`
- Image/figure overlap fixed via `[!htbp]` placement specifier enforcement in `pre_process()`
- `subcaption` package replaced with `subfig` (IEEEtran-compatible) in both paper templates
- `cleveref` + `\crefname` config added; `\balance` inserted before bibliography in both templates
- Path traversal vulnerability in `LaTeXCompiler._fix_missing_figures` — path now properly escaped
- Invalid Haiku model ID corrected (`claude-haiku-4-20250514` → `claude-haiku-4-5-20251001`) in `token_engine/router.py`
- Anthropic API calls now have structured error handling (`AuthenticationError`, `RateLimitError`, `APIStatusError`) in `token_engine/engine.py`
- Redis connection leak fixed in `/health/claude` — `aclose()` called in all code paths including error branches

### Added
- `POST /api/v1/papers/{paper_id}/compile` — LaTeX compile endpoint; runs Tectonic in a `ThreadPoolExecutor` (4 workers, 130 s timeout); returns `CompileResponse` with `pdf_b64`, `errors`, and `log`; `__scratch__` sentinel ID for scratchpad use without DB lookup; graceful `503` when Tectonic is unavailable
- `GET /api/v1/health/claude` — Claude API connectivity health check; Redis-cached (60 s TTL); auth-protected; returns model, latency_ms, cached flag
- `latex_router` registered in `backend/app/main.py` under `/api/v1`
- `get_all_models()` helper and `dict.fromkeys` ordering added to `token_engine/router.py`
- Overleaf-style split-pane LaTeX editor at `/latex-editor` dashboard route
  - CodeMirror 6 editor with LaTeX syntax highlighting (`@codemirror/legacy-modes`)
  - `.tex` and `.bib` tabs in a resizable split pane (`react-resizable-panels`)
  - Auto-compile on save with 1.5 s debounce
  - PDF preview via base64 blob URL with `URL.revokeObjectURL` cleanup
  - `localStorage` draft persistence per paper ID
- `compilePaper()` function and `CompileResponse` TypeScript interface exported from `frontend/lib/api.ts`
- `frontend/components/ui/resizable.tsx` — shadcn resizable panel wrapper
- `frontend/components/latex/` — three new components: `codemirror-editor`, `pdf-preview`, `latex-editor`
- LaTeX Editor nav item added to `frontend/components/layout/sidebar.tsx`
- New frontend dependencies: `codemirror ^6.0.2`, `@codemirror/*` suite, `react-resizable-panels ^4.10.0`
- All environment variables fully documented in `.env.example`
- LATEX FORMATTING RULES section added to `agents/ieee/prompts.py`
- LATEX FORMAT COMPLIANCE checklist added to `agents/reviewers/prompts.py`

### Changed
- `frontend` package version bumped `0.1.0 → 0.2.0`
- FastAPI app version bumped `1.0.0 → 1.1.0`

---

## [0.1.0] — 2025-06-30

- Initial release: Quorum autonomous multi-agent research platform
- IEEE, Small Paper, Blog paper generation agents
- Multi-agent review pipeline
- Token engine with model routing
- JWT auth, PostgreSQL, Redis, MinIO storage
- WebSocket real-time task progress
- APScheduler deadline management
- Production Docker Compose + Caddy reverse proxy
