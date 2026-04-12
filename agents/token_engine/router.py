"""Model routing with budget-aware downgrade logic."""

from __future__ import annotations

import enum


class BudgetStatus(enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    LOW = "low"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class BudgetExhaustedError(Exception):
    """Raised when token budget is fully consumed."""


# ---------------------------------------------------------------------------
# Model ID registry
# Verified against https://docs.anthropic.com/en/docs/about-claude/models/overview
# on 2025-Q3.  All IDs must be exact strings accepted by the Anthropic REST API.
#
# Notes on each tier:
#   deep     → claude-opus-4-20250514   ($5 / $25 per MTok — most capable)
#   standard → claude-sonnet-4-20250514 ($3 / $15 per MTok — balanced)
#   simple   → claude-haiku-4-5-20251001 ($1 / $5 per MTok — fastest/cheapest)
#
# ⚠️  There is NO model called "claude-haiku-4-20250514".  The only Claude 4
#     Haiku GA release is "claude-haiku-4-5-20251001".
# ---------------------------------------------------------------------------

TIER_TO_MODEL: dict[str, str] = {
    "deep": "claude-opus-4-20250514",
    "standard": "claude-sonnet-4-20250514",
    "simple": "claude-haiku-4-5-20251001",
}

# Cost per 1,000,000 tokens (USD) — source: Anthropic pricing page
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-opus-4-20250514": {"input": 5.0, "output": 25.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
}

DOWNGRADE_MAP: dict[str, str] = {
    "claude-opus-4-20250514": "claude-sonnet-4-20250514",
    "claude-sonnet-4-20250514": "claude-haiku-4-5-20251001",
    "claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001",
}

# Context-window limits per model (tokens) — for informational / prompt-size checks
MAX_CONTEXT_TOKENS: dict[str, int] = {
    "claude-opus-4-20250514": 200_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
}


class ModelRouter:
    """Selects the appropriate Claude model based on task tier and budget status.

    Downgrade behaviour:
        HEALTHY   – use the default model for the tier
        WARNING   – downgrade deep (Opus → Sonnet); keep others
        LOW/CRITICAL – everything goes to Haiku
        EXHAUSTED – raise ``BudgetExhaustedError``
    """

    def select_model(self, tier: str, budget_status: BudgetStatus) -> str:
        default_model = TIER_TO_MODEL[tier]

        if budget_status == BudgetStatus.HEALTHY:
            return default_model

        if budget_status == BudgetStatus.WARNING:
            if tier == "deep":
                return DOWNGRADE_MAP[default_model]
            return default_model

        if budget_status in (BudgetStatus.LOW, BudgetStatus.CRITICAL):
            return TIER_TO_MODEL["simple"]

        if budget_status == BudgetStatus.EXHAUSTED:
            raise BudgetExhaustedError(
                "Token budget exhausted. All agents paused."
            )

        return default_model

    @staticmethod
    def estimate_cost(
        model: str, est_input_tokens: int, est_output_tokens: int
    ) -> float:
        costs = MODEL_COSTS[model]
        input_cost = (est_input_tokens / 1_000_000) * costs["input"]
        output_cost = (est_output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost

    @staticmethod
    def get_model_for_tier(tier: str) -> str:
        return TIER_TO_MODEL[tier]

    @staticmethod
    def get_all_models() -> list[str]:
        """Return a deduplicated list of all configured model IDs."""
        return list(dict.fromkeys(TIER_TO_MODEL.values()))
