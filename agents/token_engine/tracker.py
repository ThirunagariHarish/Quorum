"""Usage tracking – records every Claude API call into the token_usage_logs table."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from agents.token_engine.router import MODEL_COSTS

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UsageTracker:
    """Persists token consumption records and provides aggregation queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session

    async def track(
        self,
        *,
        agent_id: uuid.UUID | str,
        task_id: uuid.UUID | str | None,
        user_id: uuid.UUID | str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        original_tier: str | None = None,
        actual_tier: str | None = None,
        was_downgraded: bool = False,
        task_phase: str | None = None,
    ) -> dict[str, Any]:
        from backend.app.models.token_usage import TokenUsageLog

        cost = self._calculate_cost(model, input_tokens, output_tokens)

        record = TokenUsageLog(
            agent_id=uuid.UUID(str(agent_id)),
            task_id=uuid.UUID(str(task_id)) if task_id else None,
            user_id=uuid.UUID(str(user_id)),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal(str(round(cost, 6))),
            original_tier=original_tier,
            actual_tier=actual_tier,
            was_downgraded=was_downgraded,
            task_phase=task_phase,
        )

        self.db.add(record)
        await self.db.flush()

        return {
            "id": str(record.id),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": float(cost),
            "was_downgraded": was_downgraded,
        }

    async def get_daily_usage(self, user_id: uuid.UUID | str) -> list[dict[str, Any]]:
        from backend.app.models.token_usage import TokenUsageLog

        today_start = datetime.combine(date.today(), datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        stmt = (
            select(TokenUsageLog)
            .where(
                TokenUsageLog.user_id == uuid.UUID(str(user_id)),
                TokenUsageLog.created_at >= today_start,
            )
            .order_by(TokenUsageLog.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "agent_id": str(r.agent_id),
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": float(r.cost_usd),
                "was_downgraded": r.was_downgraded,
                "task_phase": r.task_phase,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]

    async def get_agent_usage(
        self, user_id: uuid.UUID | str
    ) -> list[dict[str, Any]]:
        from backend.app.models.token_usage import TokenUsageLog

        stmt = (
            select(
                TokenUsageLog.agent_id,
                func.sum(TokenUsageLog.input_tokens).label("total_input"),
                func.sum(TokenUsageLog.output_tokens).label("total_output"),
                func.sum(TokenUsageLog.cost_usd).label("total_cost"),
                func.count().label("call_count"),
            )
            .where(TokenUsageLog.user_id == uuid.UUID(str(user_id)))
            .group_by(TokenUsageLog.agent_id)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "agent_id": str(row.agent_id),
                "total_input_tokens": int(row.total_input),
                "total_output_tokens": int(row.total_output),
                "total_cost_usd": float(row.total_cost),
                "call_count": int(row.call_count),
            }
            for row in rows
        ]

    @staticmethod
    def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
        return (input_tokens / 1_000_000) * costs["input"] + (
            output_tokens / 1_000_000
        ) * costs["output"]
