from __future__ import annotations

from typing import Optional

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Setting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_setting_key"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text)
    is_encrypted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    user = relationship("User", back_populates="settings")
