"""TokenBudgetEngine – cost-control wrapper for LLM calls (Anthropic, OpenAI, Google)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from agents.token_engine.classifier import TaskClassifier
from agents.token_engine.credentials import resolve_llm_for_user
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
    """Wraps LLM calls with budget enforcement and provider-aware model routing."""

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
        """Execute an LLM call with budget checks and model routing."""
        try:
            provider, api_key = await resolve_llm_for_user(self.db, self.user_id)
        except ValueError as e:
            logger.error("llm_credentials_missing: %s", e)
            raise RuntimeError(str(e)) from e

        router = ModelRouter(provider)
        tier = self.classifier.classify(agent_type, task_phase)
        budget_status = await self.check_budget()

        logger.info(
            "Budget check: provider=%s status=%s tier=%s agent=%s phase=%s",
            provider,
            budget_status.value,
            tier,
            agent_type,
            task_phase,
        )

        try:
            model = router.select_model(tier, budget_status)
        except BudgetExhaustedError as e:
            logger.warning("budget_exhausted: %s", e)
            raise

        original_model = router.get_model_for_tier(tier)
        was_downgraded = model != original_model

        if was_downgraded:
            logger.warning(
                "Model downgrade: %s → %s (budget %s)",
                original_model,
                model,
                budget_status.value,
            )

        if provider == "anthropic":
            response_text, input_tokens, output_tokens = await self._call_anthropic(
                api_key, model, prompt, system_prompt, max_tokens
            )
        elif provider == "openai":
            response_text, input_tokens, output_tokens = await self._call_openai(
                api_key, model, prompt, system_prompt, max_tokens
            )
        elif provider == "google":
            response_text, input_tokens, output_tokens = await self._call_google(
                api_key, model, prompt, system_prompt, max_tokens
            )
        else:
            raise RuntimeError(f"Unsupported LLM provider: {provider}")

        actual_tier = router.tier_from_model(model)

        if agent_id:
            await self.tracker.track(
                agent_id=agent_id,
                task_id=task_id,
                user_id=self.user_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                original_tier=tier,
                actual_tier=actual_tier,
                was_downgraded=was_downgraded,
                task_phase=task_phase,
            )

        return {
            "text": response_text,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": router.estimate_cost(model, input_tokens, output_tokens),
            "was_downgraded": was_downgraded,
            "original_tier": tier,
            "budget_status": budget_status.value,
            "llm_provider": provider,
        }

    async def _call_anthropic(
        self,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await client.messages.create(**kwargs)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        response_text = response.content[0].text if response.content else ""
        return response_text, input_tokens, output_tokens

    async def _call_openai(
        self,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        text = (resp.choices[0].message.content or "").strip()
        u = resp.usage
        if u is None:
            return text, 0, 0
        return text, u.prompt_tokens, u.completion_tokens

    async def _call_google(
        self,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        return await asyncio.to_thread(
            _google_generate_sync, model, api_key, prompt, system_prompt, max_tokens
        )


def _google_generate_sync(
    model: str,
    api_key: str,
    prompt: str,
    system_prompt: str | None,
    max_tokens: int,
) -> tuple[str, int, int]:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    if system_prompt:
        gm = genai.GenerativeModel(model, system_instruction=system_prompt)
    else:
        gm = genai.GenerativeModel(model)
    gen_config = genai.types.GenerationConfig(max_output_tokens=max_tokens)
    resp = gm.generate_content(prompt, generation_config=gen_config)
    try:
        text = (resp.text or "").strip()
    except Exception:
        text = ""
    um = getattr(resp, "usage_metadata", None)
    if um:
        pi = int(getattr(um, "prompt_token_count", 0) or 0)
        co = int(getattr(um, "candidates_token_count", 0) or 0)
    else:
        pi, co = 0, 0
    return text, pi, co
