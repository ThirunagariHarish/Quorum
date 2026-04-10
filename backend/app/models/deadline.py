from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Deadline(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "deadlines"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    venue_name: Mapped[str] = mapped_column(String(200), nullable=False)
    venue_type: Mapped[str] = mapped_column(String(20), nullable=False)
    submission_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    notification_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    venue_url: Mapped[Optional[str]] = mapped_column(String(500))
    topics: Mapped[Optional[list]] = mapped_column(JSONB)
    page_limit: Mapped[Optional[int]] = mapped_column(Integer)
    format_notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", index=True
    )

    user = relationship("User", back_populates="deadlines")
