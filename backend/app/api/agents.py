from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.agent import Agent
from backend.app.models.task import AgentTask
from backend.app.models.user import User
from backend.app.schemas.agent import (
    AgentListResponse,
    AgentResponse,
    CurrentTaskBrief,
    TaskCreateRequest,
    TaskResponse,
)

router = APIRouter(prefix="/agents", tags=["agents"])
logger = structlog.get_logger()


@router.get("", response_model=AgentListResponse)
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).order_by(Agent.name))
    agents = result.scalars().all()

    items = []
    for a in agents:
        current_task = None
        if a.current_task_id:
            task_result = await db.execute(
                select(AgentTask).where(AgentTask.id == a.current_task_id)
            )
            task = task_result.scalar_one_or_none()
            if task:
                current_task = CurrentTaskBrief(
                    id=task.id, topic=task.topic, phase=task.task_phase
                )

        items.append(
            AgentResponse(
                id=a.id,
                name=a.name,
                agent_type=a.agent_type,
                default_model=a.default_model,
                status=a.status,
                current_task=current_task,
                total_tokens_used=a.total_tokens_used,
                total_cost_usd=float(a.total_cost_usd),
                last_active_at=a.last_active_at,
                created_at=a.created_at,
            )
        )

    return AgentListResponse(items=items)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    current_task = None
    if agent.current_task_id:
        task_result = await db.execute(
            select(AgentTask).where(AgentTask.id == agent.current_task_id)
        )
        task = task_result.scalar_one_or_none()
        if task:
            current_task = CurrentTaskBrief(
                id=task.id, topic=task.topic, phase=task.task_phase
            )

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        agent_type=agent.agent_type,
        default_model=agent.default_model,
        status=agent.status,
        current_task=current_task,
        total_tokens_used=agent.total_tokens_used,
        total_cost_usd=float(agent.total_cost_usd),
        last_active_at=agent.last_active_at,
        created_at=agent.created_at,
    )


@router.get("/{agent_id}/tasks", response_model=list[TaskResponse])
async def list_agent_tasks(
    agent_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentTask).where(AgentTask.agent_id == agent_id)

    if status_filter:
        query = query.where(AgentTask.status == status_filter)

    query = query.order_by(AgentTask.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    tasks = result.scalars().all()
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post(
    "/{agent_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED
)
async def create_agent_task(
    agent_id: str,
    body: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if agent.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent is currently busy with another task",
        )

    task = AgentTask(
        agent_id=agent.id,
        user_id=current_user.id,
        topic=body.topic,
        content_type=body.content_type,
        target_venue=body.target_venue,
        target_deadline_id=body.target_deadline_id,
        priority=body.priority,
        input_data={"reference_papers": body.reference_papers} if body.reference_papers else None,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    logger.info(
        "task_created",
        task_id=str(task.id),
        agent_id=agent_id,
        topic=body.topic,
    )
    return TaskResponse.model_validate(task)
