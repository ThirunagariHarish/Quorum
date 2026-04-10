from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class UsageDataPoint(BaseModel):
    date: str
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    api_calls: int
    downgrades: int = 0


class UsageSummary(BaseModel):
    period_cost: float
    daily_budget: Optional[float] = None
    daily_remaining: Optional[float] = None
    monthly_cost: float
    monthly_budget: Optional[float] = None
    monthly_remaining: Optional[float] = None


class TokenUsageResponse(BaseModel):
    data: list[UsageDataPoint]
    summary: UsageSummary


class BudgetResponse(BaseModel):
    daily_limit_usd: Optional[float] = None
    monthly_limit_usd: Optional[float] = None
    daily_spent: float
    monthly_spent: float
    budget_status: str
    auto_downgrade_enabled: bool
    pause_on_exhaustion: bool


class BudgetUpdateRequest(BaseModel):
    daily_limit_usd: Optional[float] = None
    monthly_limit_usd: Optional[float] = None
    auto_downgrade_enabled: Optional[bool] = None
    pause_on_exhaustion: Optional[bool] = None


class ForecastResponse(BaseModel):
    forecast_30d_usd: float
    daily_average_7d: float
    trend: str
    projected_monthly: float
