from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.agent import Agent
from backend.app.models.paper import Paper
from backend.app.models.user import User
from backend.app.schemas.paper import (
    PaperDownloadResponse,
    PaperListItem,
    PaperListResponse,
    PaperResponse,
    PaperVersionBrief,
    ReviewBrief,
)
from backend.app.services.storage import storage_service

router = APIRouter(prefix="/papers", tags=["papers"])
logger = structlog.get_logger()


@router.get("", response_model=PaperListResponse)
async def list_papers(
    status_filter: Optional[str] = Query(None, alias="status"),
    paper_type: Optional[str] = None,
    agent_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Paper).where(Paper.user_id == current_user.id)

    if status_filter:
        query = query.where(Paper.status == status_filter)
    if paper_type:
        query = query.where(Paper.paper_type == paper_type)
    if agent_id:
        query = query.where(Paper.agent_id == agent_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    sort_col = getattr(Paper, sort_by, Paper.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.options(selectinload(Paper.agent))

    result = await db.execute(query)
    papers = result.scalars().all()

    items = []
    for p in papers:
        item = PaperListItem(
            id=p.id,
            title=p.title,
            abstract=p.abstract,
            paper_type=p.paper_type,
            status=p.status,
            current_version=p.current_version,
            keywords=p.keywords,
            target_venue=p.target_venue,
            plagiarism_score=float(p.plagiarism_score) if p.plagiarism_score else None,
            review_cycles=p.review_cycles,
            agent_name=p.agent.name if p.agent else None,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        items.append(item)

    return PaperListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Paper)
        .where(Paper.id == paper_id, Paper.user_id == current_user.id)
        .options(
            selectinload(Paper.agent),
            selectinload(Paper.versions),
            selectinload(Paper.reviews),
        )
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    pdf_url = None
    if paper.pdf_file_key:
        pdf_url = storage_service.get_presigned_url("papers", paper.pdf_file_key)

    versions = [
        PaperVersionBrief(
            version=v.version_number,
            created_at=v.created_at,
            change_summary=v.change_summary,
        )
        for v in paper.versions
    ]

    reviews = [
        ReviewBrief(
            id=r.id,
            verdict=r.verdict,
            quality=r.overall_quality,
            created_at=r.created_at,
        )
        for r in paper.reviews
    ]

    return PaperResponse(
        id=paper.id,
        title=paper.title,
        abstract=paper.abstract,
        paper_type=paper.paper_type,
        status=paper.status,
        current_version=paper.current_version,
        keywords=paper.keywords,
        target_venue=paper.target_venue,
        plagiarism_score=float(paper.plagiarism_score) if paper.plagiarism_score else None,
        review_cycles=paper.review_cycles,
        storage_prefix=paper.storage_prefix,
        pdf_url=pdf_url,
        agent_name=paper.agent.name if paper.agent else None,
        versions=versions,
        reviews=reviews,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )


@router.get("/{paper_id}/download", response_model=PaperDownloadResponse)
async def download_paper(
    paper_id: str,
    format: str = Query("pdf"),
    version: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Paper)
        .where(Paper.id == paper_id, Paper.user_id == current_user.id)
        .options(selectinload(Paper.versions))
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    file_key = None
    if version:
        for v in paper.versions:
            if v.version_number == version:
                file_key = v.pdf_file_key if format == "pdf" else v.latex_file_key
                break
        if not file_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
            )
    else:
        file_key = paper.pdf_file_key if format == "pdf" else paper.latex_file_key

    if not file_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not available"
        )

    download_url = storage_service.get_presigned_url("papers", file_key)
    ext = "pdf" if format == "pdf" else "tex"
    slug = paper.title[:50].lower().replace(" ", "-")
    filename = f"{slug}.{ext}"

    return PaperDownloadResponse(download_url=download_url, filename=filename)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.user_id == current_user.id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    if paper.storage_prefix:
        try:
            storage_service.delete_file("papers", paper.storage_prefix)
        except Exception:
            logger.warning("failed_to_delete_storage", prefix=paper.storage_prefix)

    await db.delete(paper)
    logger.info("paper_deleted", paper_id=str(paper.id))
