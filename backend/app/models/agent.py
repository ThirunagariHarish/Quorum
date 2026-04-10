from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Agent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    default_model: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idle", server_default="idle")
    current_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    total_tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    total_cost_usd: Mapped[float] = mapped_column(
        Numeric(10, 4), default=0, server_default="0"
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    system_prompt_ref: Mapped[Optional[str]] = mapped_column(String(255))

    tasks = relationship("AgentTask", back_populates="agent", foreign_keys="AgentTask.agent_id")
    papers = relationship("Paper", back_populates="agent")
    reviews = relationship("Review", back_populates="reviewer_agent")
    comments = relationship("Comment", back_populates="agent")
    token_usage_logs = relationship("TokenUsageLog", back_populates="agent")
