from __future__ import annotations

from typing import Optional

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDMixin


class TokenUsageLog(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "token_usage_logs"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    original_tier: Mapped[Optional[str]] = mapped_column(String(20))
    actual_tier: Mapped[Optional[str]] = mapped_column(String(20))
    was_downgraded: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    task_phase: Mapped[Optional[str]] = mapped_column(String(50))

    agent = relationship("Agent", back_populates="token_usage_logs")
    task = relationship("AgentTask", back_populates="token_usage_logs")
    user = relationship("User", back_populates="token_usage_logs")
