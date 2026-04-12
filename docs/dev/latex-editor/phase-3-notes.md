# Phase 3 — Overleaf-style LaTeX Editor: Implementation Notes

## Overview
Implemented an embedded LaTeX editor page with a split-pane layout (left = CodeMirror 6 source editor with `.tex`/`.bib` tabs, right = compiled PDF preview) and a backend compile endpoint backed by the existing `LaTeXCompiler` / Tectonic.

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/api/latex.py` | New FastAPI router — `POST /api/v1/papers/{paper_id}/compile` |
| `frontend/components/ui/resizable.tsx` | shadcn-style wrapper over `react-resizable-panels` v4 |
| `frontend/components/latex/codemirror-editor.tsx` | Controlled CodeMirror 6 editor with LaTeX (`stex`) and Markdown (`.bib`) modes |
| `frontend/components/latex/pdf-preview.tsx` | PDF preview panel — base64 → Blob → object-URL → `<iframe>` |
| `frontend/components/latex/latex-editor.tsx` | Main split-pane editor with toolbar, debounced auto-compile, localStorage draft persistence |
| `frontend/app/(dashboard)/latex-editor/page.tsx` | Dashboard page: header with paper selector dropdown + `LatexEditor` |

## Files Modified

| File | Change |
|------|--------|
| `backend/app/main.py` | Imported `latex_router` and registered it under `/api/v1` |
| `frontend/lib/api.ts` | Added `compilePaper(paperId, texContent, bibContent)` method |
| `frontend/components/layout/sidebar.tsx` | Added "LaTeX Editor" nav item with `FileCode2` icon |

---

## npm Packages Added

```
@codemirror/view @codemirror/state @codemirror/commands
@codemirror/language @codemirror/lang-markdown @codemirror/legacy-modes
codemirror react-resizable-panels
```

**Note on `react-resizable-panels` v4 API change**: The package installed was v4.10.0. v4 renames the `direction` prop on `PanelGroup` → `orientation`, and renames exported components (`PanelGroup` → `Group`, `PanelResizeHandle` → `Separator`). Our `resizable.tsx` wrapper accepts the old shadcn-style `direction` prop and maps it to `orientation` internally, preserving backward compatibility with any future consumers.

---

## Auto-Compile Debounce — How It Works

```
User types in .tex or .bib editor
  │
  ▼
handleTexChange / handleBibChange called
  │
  ├─ setState (updates editor value)
  │
  └─ scheduleCompile()
        │
        ├─ clearTimeout(debounceRef.current)   ← cancels any pending timer
        └─ setTimeout(compile, 1500ms)         ← arms a new 1.5 s timer
```

- Only when the user **stops typing** for ≥ 1.5 s does `compile()` fire.
- `compile()` sets `isCompiling=true`, calls `api.compilePaper()` (`POST /api/v1/papers/{id}/compile`), then either sets `pdfB64` (success) or `compileErrors` (failure).
- The debounce timer ref is cleaned up on unmount via `useEffect` cleanup.
- Manual "Compile" button bypasses the timer and calls `compile()` directly.

---

## Backend Compile Endpoint

```
POST /api/v1/papers/{paper_id}/compile
Authorization: Bearer <token>
Body: { "tex_content": "...", "bib_content": "..." }

Success response:
  { "success": true, "pdf_b64": "<base64-pdf>", "errors": [], "log": "..." }

Failure response:
  { "success": false, "pdf_b64": null, "errors": ["line 5: undefined control ..."], "log": "..." }
```

- Uses `asyncio.wait_for(loop.run_in_executor(_executor, _compile_sync, tex, bib), timeout=60)` to run `LaTeXCompiler.compile()` non-blocking in a thread-pool executor.
- If Tectonic is not installed, the endpoint returns HTTP 503.
- `paper_id` is validated only via auth (must be logged in); no DB lookup is needed since this is purely a compile service.

---

## PDF Rendering

1. Backend returns `pdf_b64` (plain base64, no data-URL prefix).
2. `PdfPreview` decodes it with `atob()`, wraps it in a `Blob` with `type: application/pdf`, creates an object URL via `URL.createObjectURL()`.
3. The object URL is placed in an `<iframe src={objectUrl}>`.
4. Previous object URLs are revoked on each new compile to prevent memory leaks.

---

## LocalStorage Draft Persistence

Draft content is persisted to:
- `paperpilot_latex_draft_tex_<paperId>` — `.tex` content
- `paperpilot_latex_draft_bib_<paperId>` — `.bib` content

Initial state hydrates from localStorage (falling back to `initialTex` prop or the built-in template). The editor is keyed on `paperId` so switching papers fully remounts the CodeMirror instance.

---

## Deviations from Architecture Spec

| Spec | Actual | Reason |
|------|--------|--------|
| "Save button persists .tex to papers API" | Saves draft to localStorage only | The existing `papers` API has no PATCH for raw `.tex` content; a proper "update content" endpoint would need a new DB migration. Stubbed with localStorage save and a clear toast to guide follow-up work. |
| `@codemirror/lang-markdown` for both tabs | `.tex` uses `stex` via `@codemirror/legacy-modes` | Better LaTeX syntax highlighting with minimal overhead. `.bib` uses markdown as the spec suggested. |

---

## Open Risks

1. **Tectonic availability**: The compile endpoint silently returns HTTP 503 if `tectonic` is not in `PATH`. A health-check flag could surface this in the UI.
2. **Large PDFs over the wire**: Base64-encoded PDFs can be large. A future improvement would be to upload the compiled PDF to MinIO and return a presigned URL instead.
3. **Concurrent compiles**: The thread-pool executor has `max_workers=4`. Under high concurrency, requests queue. Consider per-paper locking if needed.
4. **`.bib` file name hardcoded**: `LaTeXCompiler` writes the bib file as `references.bib`. The `.tex` source must `\bibliography{references}` for citations to resolve.
