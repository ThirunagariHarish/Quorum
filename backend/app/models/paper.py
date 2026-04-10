from __future__ import annotations

from typing import Optional

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Paper(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "papers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id")
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    paper_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    current_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    keywords: Mapped[Optional[list]] = mapped_column(JSONB)
    target_venue: Mapped[Optional[str]] = mapped_column(String(200))
    target_deadline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deadlines.id")
    )
    storage_prefix: Mapped[Optional[str]] = mapped_column(String(500))
    latex_file_key: Mapped[Optional[str]] = mapped_column(String(500))
    pdf_file_key: Mapped[Optional[str]] = mapped_column(String(500))
    markdown_file_keys: Mapped[Optional[list]] = mapped_column(JSONB)
    plagiarism_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    review_cycles: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    published_url: Mapped[Optional[str]] = mapped_column(String(500))

    user = relationship("User", back_populates="papers")
    agent = relationship("Agent", back_populates="papers")
    task = relationship("AgentTask", foreign_keys=[task_id])
    target_deadline = relationship("Deadline", foreign_keys=[target_deadline_id])
    versions = relationship(
        "PaperVersion", back_populates="paper", cascade="all, delete-orphan",
        order_by="PaperVersion.version_number",
    )
    reviews = relationship("Review", back_populates="paper", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="paper", cascade="all, delete-orphan")
    published_articles = relationship(
        "PublishedArticle", back_populates="paper", cascade="all, delete-orphan"
    )
