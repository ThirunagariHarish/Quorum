from __future__ import annotations

from typing import Optional

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.setting import Setting
from backend.app.models.token_usage import TokenUsageLog
from backend.app.models.user import User
from backend.app.schemas.token import (
    BudgetResponse,
    BudgetUpdateRequest,
    ForecastResponse,
    TokenUsageResponse,
    UsageDataPoint,
    UsageSummary,
)

router = APIRouter(prefix="/tokens", tags=["tokens"])
logger = structlog.get_logger()


async def _get_setting_value(db: AsyncSession, user_id, key: str) -> Optional[str]:
    result = await db.execute(
        select(Setting.value).where(Setting.user_id == user_id, Setting.key == key)
    )
    return result.scalar_one_or_none()


@router.get("/usage", response_model=TokenUsageResponse)
async def get_token_usage(
    agent_id: Optional[str] = None,
    model: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    granularity: str = "daily",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)

    date_trunc = func.date_trunc("day", TokenUsageLog.created_at)

    query = (
        select(
            date_trunc.label("period"),
            func.sum(TokenUsageLog.cost_usd).label("total_cost"),
            func.sum(TokenUsageLog.input_tokens).label("total_input"),
            func.sum(TokenUsageLog.output_tokens).label("total_output"),
            func.count().label("api_calls"),
            func.sum(case((TokenUsageLog.was_downgraded == True, 1), else_=0)).label(
                "downgrades"
            ),
        )
        .where(
            TokenUsageLog.user_id == current_user.id,
            TokenUsageLog.created_at >= start_dt,
            TokenUsageLog.created_at <= end_dt,
        )
        .group_by("period")
        .order_by(date_trunc.desc())
    )

    if agent_id:
        query = query.where(TokenUsageLog.agent_id == agent_id)
    if model:
        query = query.where(TokenUsageLog.model == model)

    result = await db.execute(query)
    rows = result.all()

    data = [
        UsageDataPoint(
            date=str(row.period.date()) if row.period else "",
            total_cost_usd=float(row.total_cost or 0),
            total_input_tokens=int(row.total_input or 0),
            total_output_tokens=int(row.total_output or 0),
            api_calls=int(row.api_calls or 0),
            downgrades=int(row.downgrades or 0),
        )
        for row in rows
    ]

    # Compute summary
    today = date.today()
    daily_result = await db.execute(
        select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == current_user.id,
            func.date(TokenUsageLog.created_at) == today,
        )
    )
    daily_spent = float(daily_result.scalar_one())

    month_start = today.replace(day=1)
    monthly_result = await db.execute(
        select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == current_user.id,
            func.date(TokenUsageLog.created_at) >= month_start,
        )
    )
    monthly_spent = float(monthly_result.scalar_one())

    daily_budget_str = await _get_setting_value(db, current_user.id, "daily_budget_usd")
    monthly_budget_str = await _get_setting_value(db, current_user.id, "monthly_budget_usd")
    daily_budget = float(daily_budget_str) if daily_budget_str else None
    monthly_budget = float(monthly_budget_str) if monthly_budget_str else None

    summary = UsageSummary(
        period_cost=sum(d.total_cost_usd for d in data),
        daily_budget=daily_budget,
        daily_remaining=(daily_budget - daily_spent) if daily_budget else None,
        monthly_cost=monthly_spent,
        monthly_budget=monthly_budget,
        monthly_remaining=(monthly_budget - monthly_spent) if monthly_budget else None,
    )

    return TokenUsageResponse(data=data, summary=summary)


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()

    daily_result = await db.execute(
        select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == current_user.id,
            func.date(TokenUsageLog.created_at) == today,
        )
    )
    daily_spent = float(daily_result.scalar_one())

    month_start = today.replace(day=1)
    monthly_result = await db.execute(
        select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == current_user.id,
            func.date(TokenUsageLog.created_at) >= month_start,
        )
    )
    monthly_spent = float(monthly_result.scalar_one())

    daily_budget_str = await _get_setting_value(db, current_user.id, "daily_budget_usd")
    monthly_budget_str = await _get_setting_value(db, current_user.id, "monthly_budget_usd")
    auto_downgrade_str = await _get_setting_value(db, current_user.id, "auto_downgrade")
    pause_str = await _get_setting_value(db, current_user.id, "pause_on_exhaustion")

    daily_limit = float(daily_budget_str) if daily_budget_str else None
    monthly_limit = float(monthly_budget_str) if monthly_budget_str else None

    budget_status = "ok"
    if daily_limit:
        pct_used = daily_spent / daily_limit
        if pct_used >= 1.0:
            budget_status = "exhausted"
        elif pct_used >= 0.7:
            budget_status = "warning"

    return BudgetResponse(
        daily_limit_usd=daily_limit,
        monthly_limit_usd=monthly_limit,
        daily_spent=daily_spent,
        monthly_spent=monthly_spent,
        budget_status=budget_status,
        auto_downgrade_enabled=auto_downgrade_str == "true" if auto_downgrade_str else True,
        pause_on_exhaustion=pause_str == "true" if pause_str else True,
    )


@router.put("/budget", response_model=BudgetResponse)
async def update_budget(
    body: BudgetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = {}
    if body.daily_limit_usd is not None:
        updates["daily_budget_usd"] = str(body.daily_limit_usd)
    if body.monthly_limit_usd is not None:
        updates["monthly_budget_usd"] = str(body.monthly_limit_usd)
    if body.auto_downgrade_enabled is not None:
        updates["auto_downgrade"] = str(body.auto_downgrade_enabled).lower()
    if body.pause_on_exhaustion is not None:
        updates["pause_on_exhaustion"] = str(body.pause_on_exhaustion).lower()

    for key, value in updates.items():
        result = await db.execute(
            select(Setting).where(
                Setting.user_id == current_user.id, Setting.key == key
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(
                Setting(user_id=current_user.id, key=key, value=value, is_encrypted=False)
            )

    await db.flush()
    logger.info("budget_updated", user_id=str(current_user.id))

    return await get_budget(current_user=current_user, db=db)


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    week_ago = today - timedelta(days=7)

    weekly_result = await db.execute(
        select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == current_user.id,
            func.date(TokenUsageLog.created_at) >= week_ago,
        )
    )
    weekly_cost = float(weekly_result.scalar_one())
    daily_avg = weekly_cost / 7.0 if weekly_cost > 0 else 0

    prev_week_start = today - timedelta(days=14)
    prev_weekly_result = await db.execute(
        select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
            TokenUsageLog.user_id == current_user.id,
            func.date(TokenUsageLog.created_at) >= prev_week_start,
            func.date(TokenUsageLog.created_at) < week_ago,
        )
    )
    prev_weekly_cost = float(prev_weekly_result.scalar_one())

    trend = "stable"
    if prev_weekly_cost > 0:
        change = (weekly_cost - prev_weekly_cost) / prev_weekly_cost
        if change > 0.1:
            trend = "increasing"
        elif change < -0.1:
            trend = "decreasing"

    return ForecastResponse(
        forecast_30d_usd=round(daily_avg * 30, 2),
        daily_average_7d=round(daily_avg, 2),
        trend=trend,
        projected_monthly=round(daily_avg * 30, 2),
    )
