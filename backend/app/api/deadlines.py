from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.deadline import Deadline
from backend.app.models.user import User
from backend.app.schemas.deadline import DeadlineCreateRequest, DeadlineResponse

router = APIRouter(prefix="/deadlines", tags=["deadlines"])
logger = structlog.get_logger()


@router.get("", response_model=list[DeadlineResponse])
async def list_deadlines(
    is_active: Optional[bool] = None,
    sort_by: str = "submission_deadline",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Deadline).where(Deadline.user_id == current_user.id)

    if is_active is not None:
        query = query.where(Deadline.is_active == is_active)

    sort_col = getattr(Deadline, sort_by, Deadline.submission_deadline)
    query = query.order_by(sort_col.asc())

    result = await db.execute(query)
    deadlines = result.scalars().all()
    return [DeadlineResponse.model_validate(d) for d in deadlines]


@router.post("", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    body: DeadlineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deadline = Deadline(
        user_id=current_user.id,
        venue_name=body.venue_name,
        venue_type=body.venue_type,
        submission_deadline=body.submission_deadline,
        notification_deadline=body.notification_deadline,
        venue_url=body.venue_url,
        topics=body.topics,
        page_limit=body.page_limit,
        format_notes=body.format_notes,
    )
    db.add(deadline)
    await db.flush()
    await db.refresh(deadline)

    logger.info("deadline_created", deadline_id=str(deadline.id), venue=body.venue_name)
    return DeadlineResponse.model_validate(deadline)


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deadline(
    deadline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Deadline).where(
            Deadline.id == deadline_id, Deadline.user_id == current_user.id
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deadline not found"
        )

    await db.delete(deadline)
    logger.info("deadline_deleted", deadline_id=str(deadline.id))
