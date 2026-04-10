from __future__ import annotations

from typing import Optional

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDMixin


class Review(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "reviews"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    paper_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paper_versions.id"), nullable=False
    )
    reviewer_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    overall_quality: Mapped[Optional[int]] = mapped_column(Integer)
    plagiarism_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    feedback_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    revision_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_human_review: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    paper = relationship("Paper", back_populates="reviews")
    paper_version = relationship("PaperVersion", back_populates="reviews")
    reviewer_agent = relationship("Agent", back_populates="reviews")
    comments = relationship("Comment", back_populates="review", cascade="all, delete-orphan")
