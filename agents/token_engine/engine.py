"""TokenBudgetEngine – central cost-control wrapper for every Claude API call.

Wraps the Claude Agent SDK ``query()`` with:
    1. Task classification  →  complexity tier
    2. Budget checking      →  budget status
    3. Model routing        →  model selection (with auto-downgrade)
    4. Usage tracking       →  persist to DB
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from agents.token_engine.classifier import TaskClassifier
from agents.token_engine.router import (
    BudgetExhaustedError,
    BudgetStatus,
    ModelRouter,
)
from agents.token_engine.tracker import UsageTracker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEFAULT_DAILY_LIMIT_USD = 10.0
DEFAULT_MONTHLY_LIMIT_USD = 300.0


class TokenBudgetEngine:
    """Wraps every Claude Agent SDK call with budget enforcement and model routing."""

    def __init__(
        self,
        db_session: AsyncSession,
        user_id: uuid.UUID | str,
        *,
        daily_limit_usd: float = DEFAULT_DAILY_LIMIT_USD,
        monthly_limit_usd: float = DEFAULT_MONTHLY_LIMIT_USD,
    ) -> None:
        self.db = db_session
        self.user_id = uuid.UUID(str(user_id))
        self.daily_limit_usd = daily_limit_usd
        self.monthly_limit_usd = monthly_limit_usd

        self.classifier = TaskClassifier()
        self.router = ModelRouter()
        self.tracker = UsageTracker(db_session)

    # ------------------------------------------------------------------
    # Budget status helpers
    # ------------------------------------------------------------------

    async def get_daily_spent(self) -> float:
        from backend.app.models.token_usage import TokenUsageLog

        today_start = datetime.combine(date.today(), datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        stmt = select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == self.user_id,
            TokenUsageLog.created_at >= today_start,
        )
        result = await self.db.execute(stmt)
        return float(result.scalar_one())

    async def get_monthly_spent(self) -> float:
        from backend.app.models.token_usage import TokenUsageLog

        month_start = datetime(
            date.today().year, date.today().month, 1, tzinfo=timezone.utc
        )
        stmt = select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == self.user_id,
            TokenUsageLog.created_at >= month_start,
        )
        result = await self.db.execute(stmt)
        return float(result.scalar_one())

    async def check_budget(self) -> BudgetStatus:
        daily_spent = await self.get_daily_spent()
        monthly_spent = await self.get_monthly_spent()

        daily_remaining_pct = 1.0 - (daily_spent / self.daily_limit_usd) if self.daily_limit_usd else 1.0
        monthly_remaining_pct = 1.0 - (monthly_spent / self.monthly_limit_usd) if self.monthly_limit_usd else 1.0
        remaining_pct = min(daily_remaining_pct, monthly_remaining_pct)

        if remaining_pct <= 0:
            return BudgetStatus.EXHAUSTED
        if remaining_pct < 0.10:
            return BudgetStatus.CRITICAL
        if remaining_pct < 0.30:
            return BudgetStatus.LOW
        if remaining_pct < 0.70:
            return BudgetStatus.WARNING
        return BudgetStatus.HEALTHY

    # ------------------------------------------------------------------
    # Core execution wrapper
    # ------------------------------------------------------------------

    async def execute_with_budget(
        self,
        agent_type: str,
        task_phase: str,
        prompt: str,
        *,
        agent_id: uuid.UUID | str | None = None,
        task_id: uuid.UUID | str | None = None,
        system_prompt: str | None = None,
        tools: list[Any] | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Execute a Claude API call wrapped with budget checks and model routing.

        Returns a dict containing the response text, model used, usage stats,
        and whether a downgrade was applied.
        """
        import anthropic

        tier = self.classifier.classify(agent_type, task_phase)
        budget_status = await self.check_budget()

        logger.info(
            "Budget check: status=%s tier=%s agent=%s phase=%s",
            budget_status.value,
            tier,
            agent_type,
            task_phase,
        )

        model = self.router.select_model(tier, budget_status)
        original_model = self.router.get_model_for_tier(tier)
        was_downgraded = model != original_model

        if was_downgraded:
            logger.warning(
                "Model downgrade: %s → %s (budget %s)",
                original_model,
                model,
                budget_status.value,
            )

        client = anthropic.AsyncAnthropic()
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = await client.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise ValueError(
                "Invalid Anthropic API key. Check ANTHROPIC_API_KEY in .env"
            ) from exc
        except anthropic.RateLimitError as exc:
            logger.warning(
                "Rate limited by Anthropic: %s", exc,
                extra={"agent_type": agent_type, "task_phase": task_phase},
            )
            raise
        except anthropic.APIStatusError as exc:
            logger.error(
                "Anthropic API error %s: %s",
                exc.status_code,
                exc.message,
                extra={"agent_type": agent_type, "task_phase": task_phase},
            )
            raise
        except Exception as exc:
            logger.error(
                "Unexpected error calling Claude: %s", exc,
                extra={"agent_type": agent_type, "task_phase": task_phase},
            )
            raise

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        response_text = response.content[0].text if response.content else ""

        if agent_id:
            await self.tracker.track(
                agent_id=agent_id,
                task_id=task_id,
                user_id=self.user_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                original_tier=tier,
                actual_tier=self._tier_from_model(model),
                was_downgraded=was_downgraded,
                task_phase=task_phase,
            )

        return {
            "text": response_text,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": self.router.estimate_cost(model, input_tokens, output_tokens),
            "was_downgraded": was_downgraded,
            "original_tier": tier,
            "budget_status": budget_status.value,
        }

    @staticmethod
    def _tier_from_model(model: str) -> str:
        _reverse = {
            "claude-opus-4-20250514": "deep",
            "claude-sonnet-4-20250514": "standard",
            "claude-haiku-4-5-20251001": "simple",
        }
        return _reverse.get(model, "standard")
