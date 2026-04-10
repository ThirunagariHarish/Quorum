from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDMixin


class PublishedArticle(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "published_articles"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    platform_article_id: Mapped[Optional[str]] = mapped_column(String(100))
    published_url: Mapped[str] = mapped_column(String(500), nullable=False)
    series_name: Mapped[Optional[str]] = mapped_column(String(200))
    part_number: Mapped[Optional[int]] = mapped_column(Integer)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(20), default="published", server_default="published"
    )

    paper = relationship("Paper", back_populates="published_articles")
