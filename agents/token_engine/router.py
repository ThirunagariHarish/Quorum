"""Model routing with budget-aware downgrade logic (Anthropic, OpenAI, Google Gemini)."""

from __future__ import annotations

import enum
from typing import Final


class BudgetStatus(enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    LOW = "low"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class BudgetExhaustedError(Exception):
    """Raised when token budget is fully consumed."""


# Per-provider tier → model, $/1M tokens, and downgrade chain
PROVIDER_CONFIG: Final[dict[str, dict]] = {
    "anthropic": {
        "tier_to_model": {
            "deep": "claude-opus-4-20250514",
            "standard": "claude-sonnet-4-20250514",
            "simple": "claude-haiku-4-5-20251001",
        },
        "model_costs": {
            "claude-opus-4-20250514": {"input": 5.0, "output": 25.0},
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
        },
        "downgrade_map": {
            "claude-opus-4-20250514": "claude-sonnet-4-20250514",
            "claude-sonnet-4-20250514": "claude-haiku-4-5-20251001",
            "claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001",
        },
    },
    "openai": {
        "tier_to_model": {
            "deep": "gpt-4o",
            "standard": "gpt-4o-mini",
            "simple": "gpt-4o-mini",
        },
        "model_costs": {
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        },
        "downgrade_map": {
            "gpt-4o": "gpt-4o-mini",
            "gpt-4o-mini": "gpt-4o-mini",
        },
    },
    "google": {
        "tier_to_model": {
            "deep": "gemini-2.0-flash",
            "standard": "gemini-2.0-flash",
            "simple": "gemini-2.0-flash",
        },
        "model_costs": {
            "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
        },
        "downgrade_map": {
            "gemini-2.0-flash": "gemini-2.0-flash",
        },
    },
}

# Flattened for usage tracker cost estimation
MODEL_COSTS: dict[str, dict[str, float]] = {}
for _cfg in PROVIDER_CONFIG.values():
    MODEL_COSTS.update(_cfg["model_costs"])


class ModelRouter:
    """Selects model by task tier, budget, and LLM provider."""

    def __init__(self, provider: str = "anthropic") -> None:
        self.provider = provider if provider in PROVIDER_CONFIG else "anthropic"
        self._cfg = PROVIDER_CONFIG[self.provider]

    def select_model(self, tier: str, budget_status: BudgetStatus) -> str:
        tier_to_model = self._cfg["tier_to_model"]
        downgrade_map = self._cfg["downgrade_map"]
        default_model = tier_to_model.get(tier) or tier_to_model["standard"]
        floor_model = tier_to_model["simple"]

        if budget_status == BudgetStatus.HEALTHY:
            return default_model

        if budget_status == BudgetStatus.WARNING:
            if tier == "deep":
                return downgrade_map.get(default_model, default_model)
            return default_model

        if budget_status in (BudgetStatus.LOW, BudgetStatus.CRITICAL):
            return floor_model

        if budget_status == BudgetStatus.EXHAUSTED:
            raise BudgetExhaustedError("Token budget exhausted. All agents paused.")

        return default_model

    @staticmethod
    def estimate_cost(
        model: str, est_input_tokens: int, est_output_tokens: int
    ) -> float:
        costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
        input_cost = (est_input_tokens / 1_000_000) * costs["input"]
        output_cost = (est_output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost

    def get_model_for_tier(self, tier: str) -> str:
        tier_to_model = self._cfg["tier_to_model"]
        return tier_to_model.get(tier) or tier_to_model["standard"]

    def tier_from_model(self, model: str) -> str:
        tier_to_model = self._cfg["tier_to_model"]
        for tier, m in tier_to_model.items():
            if m == model:
                return tier
        return "standard"

    def get_all_models(self) -> list[str]:
        """Return a deduplicated list of all configured model IDs for this provider."""
        return list(dict.fromkeys(self._cfg["tier_to_model"].values()))
