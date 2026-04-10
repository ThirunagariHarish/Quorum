from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan")
    papers = relationship("Paper", back_populates="user")
    tasks = relationship("AgentTask", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    token_usage_logs = relationship("TokenUsageLog", back_populates="user")
    deadlines = relationship("Deadline", back_populates="user")
