from __future__ import annotations

from typing import Optional

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDMixin


class Comment(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "comments"

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    is_resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    review = relationship("Review", back_populates="comments")
    paper = relationship("Paper", back_populates="comments")
    user = relationship("User", back_populates="comments")
    agent = relationship("Agent", back_populates="comments")
