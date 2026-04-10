from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class AgentTask(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_tasks"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    task_phase: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        String(20), default="queued", server_default="queued", index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    output_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    target_venue: Mapped[Optional[str]] = mapped_column(String(200))
    target_deadline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deadlines.id")
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255))
    model_used: Mapped[Optional[str]] = mapped_column(String(50))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    agent = relationship("Agent", back_populates="tasks", foreign_keys=[agent_id])
    user = relationship("User", back_populates="tasks")
    parent_task = relationship("AgentTask", remote_side="AgentTask.id", backref="sub_tasks")
    target_deadline = relationship("Deadline", foreign_keys=[target_deadline_id])
    token_usage_logs = relationship("TokenUsageLog", back_populates="task")
