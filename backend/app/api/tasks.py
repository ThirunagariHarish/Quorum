from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.task import AgentTask
from backend.app.models.user import User
from backend.app.schemas.agent import TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = structlog.get_logger()


class TaskUpdateRequest:
    def __init__(
        self,
        status: Optional[str] = None,
        priority: Optional[int] = None,
    ):
        self.status = status
        self.priority = priority


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    agent_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    content_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentTask).where(AgentTask.user_id == current_user.id)

    if agent_id:
        query = query.where(AgentTask.agent_id == agent_id)
    if status_filter:
        query = query.where(AgentTask.status == status_filter)
    if content_type:
        query = query.where(AgentTask.content_type == content_type)

    query = query.order_by(AgentTask.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    tasks = result.scalars().all()
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentTask).where(
            AgentTask.id == task_id, AgentTask.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentTask).where(
            AgentTask.id == task_id, AgentTask.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if "status" in body:
        allowed_transitions = {
            "queued": ["running", "cancelled"],
            "running": ["completed", "failed", "cancelled"],
        }
        allowed = allowed_transitions.get(task.status, [])
        if body["status"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{task.status}' to '{body['status']}'",
            )
        task.status = body["status"]

    if "priority" in body:
        task.priority = body["priority"]

    await db.flush()
    await db.refresh(task)

    logger.info("task_updated", task_id=str(task.id), updates=body)
    return TaskResponse.model_validate(task)
