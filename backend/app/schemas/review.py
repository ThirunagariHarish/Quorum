from __future__ import annotations

from typing import Optional

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReviewCreateRequest(BaseModel):
    paper_id: UUID
    verdict: str
    summary: Optional[str] = None
    overall_quality: Optional[int] = None


class ReviewResponse(BaseModel):
    id: UUID
    paper_id: UUID
    paper_version_id: UUID
    reviewer_agent_id: UUID
    verdict: str
    overall_quality: Optional[int] = None
    plagiarism_score: Optional[float] = None
    feedback_json: Optional[dict] = None
    summary: Optional[str] = None
    revision_number: int
    is_human_review: bool
    comments: list["CommentResponse"] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreateRequest(BaseModel):
    content: str
    severity: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None


class CommentResponse(BaseModel):
    id: UUID
    review_id: Optional[UUID] = None
    paper_id: UUID
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    content: str
    severity: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    is_resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
