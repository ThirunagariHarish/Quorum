from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.comment import Comment
from backend.app.models.paper import Paper
from backend.app.models.paper_version import PaperVersion
from backend.app.models.review import Review
from backend.app.models.user import User
from backend.app.schemas.review import (
    CommentCreateRequest,
    CommentResponse,
    ReviewCreateRequest,
    ReviewResponse,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])
logger = structlog.get_logger()


@router.get("", response_model=list[ReviewResponse])
async def list_reviews(
    paper_id: Optional[str] = None,
    verdict: Optional[str] = None,
    is_human_review: Optional[bool] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Review)
        .join(Paper, Review.paper_id == Paper.id)
        .where(Paper.user_id == current_user.id)
        .options(selectinload(Review.comments))
    )

    if paper_id:
        query = query.where(Review.paper_id == paper_id)
    if verdict:
        query = query.where(Review.verdict == verdict)
    if is_human_review is not None:
        query = query.where(Review.is_human_review == is_human_review)

    query = query.order_by(Review.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    reviews = result.scalars().unique().all()
    return [ReviewResponse.model_validate(r) for r in reviews]


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    body: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    paper_result = await db.execute(
        select(Paper)
        .where(Paper.id == body.paper_id, Paper.user_id == current_user.id)
        .options(selectinload(Paper.versions))
    )
    paper = paper_result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    latest_version = None
    for v in paper.versions:
        if latest_version is None or v.version_number > latest_version.version_number:
            latest_version = v

    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper has no versions to review",
        )

    # For human reviews, use a placeholder reviewer_agent_id (first agent)
    from backend.app.models.agent import Agent
    agent_result = await db.execute(select(Agent).limit(1))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No agents configured",
        )

    review = Review(
        paper_id=paper.id,
        paper_version_id=latest_version.id,
        reviewer_agent_id=agent.id,
        verdict=body.verdict,
        overall_quality=body.overall_quality,
        summary=body.summary,
        is_human_review=True,
        revision_number=paper.review_cycles + 1,
    )
    db.add(review)

    paper.review_cycles += 1
    if body.verdict == "approve":
        paper.status = "approved"
    elif body.verdict == "revise":
        paper.status = "revisions_requested"
    elif body.verdict == "reject":
        paper.status = "rejected"

    await db.flush()
    await db.refresh(review)

    logger.info("review_created", review_id=str(review.id), verdict=body.verdict)
    return ReviewResponse.model_validate(review)


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Review)
        .where(Review.id == review_id)
        .options(selectinload(Review.comments))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    return ReviewResponse.model_validate(review)


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Review).where(Review.id == review_id).options(selectinload(Review.comments))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    if "verdict" in body:
        review.verdict = body["verdict"]
    if "summary" in body:
        review.summary = body["summary"]
    if "overall_quality" in body:
        review.overall_quality = body["overall_quality"]

    await db.flush()
    await db.refresh(review)
    return ReviewResponse.model_validate(review)


@router.post(
    "/{review_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    review_id: str,
    body: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    comment = Comment(
        review_id=review.id,
        paper_id=review.paper_id,
        user_id=current_user.id,
        content=body.content,
        severity=body.severity,
        category=body.category,
        location=body.location,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    return CommentResponse.model_validate(comment)


@router.get("/{review_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comment)
        .where(Comment.review_id == review_id)
        .order_by(Comment.created_at.asc())
    )
    comments = result.scalars().all()
    return [CommentResponse.model_validate(c) for c in comments]


@router.post("/{review_id}/submit-feedback")
async def submit_feedback(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Review).where(Review.id == review_id).options(selectinload(Review.comments))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    paper_result = await db.execute(select(Paper).where(Paper.id == review.paper_id))
    paper = paper_result.scalar_one_or_none()
    if paper:
        paper.status = "revisions_requested"

    logger.info("feedback_submitted", review_id=str(review.id))

    return {
        "task_id": None,
        "message": "Feedback sent. Agent will begin revision.",
        "revision_number": review.revision_number + 1,
    }


@router.post("/{review_id}/approve")
async def approve_paper(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    review.verdict = "approve"

    paper_result = await db.execute(select(Paper).where(Paper.id == review.paper_id))
    paper = paper_result.scalar_one_or_none()
    if paper:
        paper.status = "approved"

    await db.flush()
    logger.info("paper_approved", paper_id=str(review.paper_id))

    return {
        "paper_id": str(review.paper_id),
        "status": "approved",
        "message": "Paper approved and moved to approved files.",
    }
