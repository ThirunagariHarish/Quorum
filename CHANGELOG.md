# Changelog

All notable changes to PaperPilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

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
