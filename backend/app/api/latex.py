"""LaTeX compile endpoint — wraps the shared LaTeXCompiler in an async executor."""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import structlog

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.paper import Paper
from backend.app.models.user import User

# LaTeXCompiler lives in agents/shared/latex.py (import at call-time to avoid
# circular‐import issues if agents/ is on sys.path).
try:
    from agents.shared.latex import LaTeXCompiler  # type: ignore[import]
    _compiler = LaTeXCompiler()
    _TECTONIC_AVAILABLE = True
except ImportError:
    _TECTONIC_AVAILABLE = False
    _compiler = None  # type: ignore[assignment]

router = APIRouter(prefix="/papers", tags=["latex"])
logger = structlog.get_logger()

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

COMPILE_TIMEOUT_SECONDS = 130  # 10 s buffer above the 120 s subprocess timeout

# Scratch-pad sentinel — skips paper ownership check intentionally.
SCRATCH_ID = "__scratch__"


class CompileRequest(BaseModel):
    tex_content: str = Field(..., max_length=5_000_000)   # 5 MB cap
    bib_content: str = Field("", max_length=1_000_000)    # 1 MB cap


class CompileResponse(BaseModel):
    success: bool
    pdf_b64: str | None = None
    errors: list[str] = []
    log: str = ""


@router.post("/{paper_id}/compile", response_model=CompileResponse)
async def compile_paper(
    paper_id: str,
    body: CompileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompileResponse:
    """Compile LaTeX source to PDF via Tectonic and return the result as base64."""

    if not _TECTONIC_AVAILABLE or _compiler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LaTeX compiler (Tectonic) is not available on this server.",
        )

    # Ownership check — scratch-pad sentinel bypasses DB lookup intentionally.
    if paper_id != SCRATCH_ID:
        result = await db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == current_user.id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Paper not found")

    logger.info(
        "latex_compile_requested",
        paper_id=paper_id,
        user_id=str(current_user.id),
        tex_bytes=len(body.tex_content),
    )

    loop = asyncio.get_running_loop()

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                _compile_sync,
                body.tex_content,
                body.bib_content,
            ),
            timeout=COMPILE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("latex_compile_timeout", paper_id=paper_id)
        return CompileResponse(
            success=False,
            errors=["Compilation timed out after 130 seconds."],
        )
    except Exception as exc:
        logger.exception("latex_compile_error", paper_id=paper_id, error=str(exc))
        return CompileResponse(success=False, errors=[str(exc)])

    if result.success and result.pdf_bytes:
        pdf_b64 = base64.b64encode(result.pdf_bytes).decode("ascii")
        logger.info(
            "latex_compile_success",
            paper_id=paper_id,
            pdf_bytes=len(result.pdf_bytes),
        )
        return CompileResponse(success=True, pdf_b64=pdf_b64, log=result.log)

    logger.warning(
        "latex_compile_failed",
        paper_id=paper_id,
        errors=result.errors,
    )
    return CompileResponse(success=False, errors=result.errors, log=result.log)


def _compile_sync(tex_content: str, bib_content: str) -> object:
    """Thin synchronous wrapper called from the thread-pool executor."""
    return _compiler.compile(  # type: ignore[union-attr]
        tex_content=tex_content,
        bib_content=bib_content or None,
    )
