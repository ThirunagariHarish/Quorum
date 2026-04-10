from __future__ import annotations

from typing import Optional

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DeadlineCreateRequest(BaseModel):
    venue_name: str
    venue_type: str
    submission_deadline: datetime
    notification_deadline: Optional[datetime] = None
    venue_url: Optional[str] = None
    topics: Optional[list[str]] = None
    page_limit: Optional[int] = None
    format_notes: Optional[str] = None


class DeadlineResponse(BaseModel):
    id: UUID
    user_id: UUID
    venue_name: str
    venue_type: str
    submission_deadline: datetime
    notification_deadline: Optional[datetime] = None
    venue_url: Optional[str] = None
    topics: Optional[list] = None
    page_limit: Optional[int] = None
    format_notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
