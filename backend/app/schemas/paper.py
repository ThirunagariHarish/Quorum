from __future__ import annotations

from typing import Optional

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PaperVersionBrief(BaseModel):
    version: int
    created_at: datetime
    change_summary: Optional[str] = None

    model_config = {"from_attributes": True}


class ReviewBrief(BaseModel):
    id: UUID
    verdict: str
    quality: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaperResponse(BaseModel):
    id: UUID
    title: str
    abstract: Optional[str] = None
    paper_type: str
    status: str
    current_version: int
    keywords: Optional[list] = None
    target_venue: Optional[str] = None
    plagiarism_score: Optional[float] = None
    review_cycles: int
    storage_prefix: Optional[str] = None
    pdf_url: Optional[str] = None
    agent_name: Optional[str] = None
    versions: list[PaperVersionBrief] = []
    reviews: list[ReviewBrief] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperListItem(BaseModel):
    id: UUID
    title: str
    abstract: Optional[str] = None
    paper_type: str
    status: str
    current_version: int
    keywords: Optional[list] = None
    target_venue: Optional[str] = None
    plagiarism_score: Optional[float] = None
    review_cycles: int
    agent_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperListResponse(BaseModel):
    items: list[PaperListItem]
    total: int
    page: int
    per_page: int


class PaperDownloadResponse(BaseModel):
    download_url: str
    filename: str
    expires_in: int = 3600
