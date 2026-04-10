from __future__ import annotations

from typing import Optional

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PublishRequest(BaseModel):
    paper_id: UUID
    part_number: Optional[int] = None
    published: bool = False
    tags: Optional[list[str]] = None


class PublishResponse(BaseModel):
    id: UUID
    platform: str
    platform_article_id: Optional[str] = None
    published_url: str
    status: str
    published_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
