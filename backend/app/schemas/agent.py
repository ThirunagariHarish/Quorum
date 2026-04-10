from __future__ import annotations

from typing import Optional

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CurrentTaskBrief(BaseModel):
    id: UUID
    topic: str
    phase: Optional[str] = None

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    id: UUID
    name: str
    agent_type: str
    default_model: str
    status: str
    current_task: Optional[CurrentTaskBrief] = None
    total_tokens_used: int
    total_cost_usd: float
    last_active_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentResponse]


class TaskCreateRequest(BaseModel):
    topic: str
    content_type: str
    target_venue: Optional[str] = None
    reference_papers: Optional[list[dict]] = None
    priority: int = 5
    target_deadline_id: Optional[UUID] = None


class TaskResponse(BaseModel):
    id: UUID
    agent_id: UUID
    parent_task_id: Optional[UUID] = None
    topic: str
    content_type: str
    task_phase: Optional[str] = None
    status: str
    priority: int
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    target_venue: Optional[str] = None
    model_used: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
