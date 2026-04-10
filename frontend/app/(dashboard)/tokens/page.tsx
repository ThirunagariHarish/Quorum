"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { DailySpendChart } from "@/components/charts/daily-spend-chart";
import { AgentCostChart } from "@/components/charts/agent-cost-chart";
import { ModelCostChart } from "@/components/charts/model-cost-chart";
import { useTokenStore } from "@/stores/token-store";
import { formatCurrency } from "@/lib/utils";
import { TrendingDown, TrendingUp, Zap, Target } from "lucide-react";
import api from "@/lib/api";

export default function TokensPage() {
  const { dailyUsage, summary, budget, forecast, fetchUsage, fetchBudget, fetchForecast } =
    useTokenStore();
  const [loading, setLoading] = useState(true);
  const [agentCostData, setAgentCostData] = useState<{ name: string; value: number }[]>([]);
  const [modelCostData, setModelCostData] = useState<{ model: string; cost: number }[]>([]);

  useEffect(() => {
    Promise.all([fetchUsage(), fetchBudget(), fetchForecast()]).finally(() =>
      setLoading(false)
    );

    api
      .getAgents()
      .then((res) => {
        setAgentCostData(
          res.items.map((a) => ({ name: a.name, value: a.total_cost_usd }))
        );
      })
      .catch(() => {});

    setModelCostData([
      { model: "Haiku", cost: 0 },
      { model: "Sonnet", cost: 0 },
      { model: "Opus", cost: 0 },
    ]);
  }, [fetchUsage, fetchBudget, fetchForecast]);

  const dailyPct = summary?.daily_budget
    ? Math.round(
        ((summary.daily_budget - (summary.daily_remaining ?? 0)) / summary.daily_budget) * 100
      )
    : 0;
  const monthlyPct = summary?.monthly_budget
    ? Math.round(
        ((summary.monthly_budget - (summary.monthly_remaining ?? 0)) / summary.monthly_budget) * 100
      )
    : 0;

  const todayDowngrades = dailyUsage.length > 0 ? dailyUsage[dailyUsage.length - 1]?.downgrades ?? 0 : 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-80" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Token Usage</h2>
        <p className="text-muted-foreground">Monitor API costs and budget consumption</p>
      </div>

      {/* Budget Progress */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Daily Budget</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Progress value={dailyPct} className="h-3" />
            <div className="flex justify-between text-sm">
              <span>
                {summary ? formatCurrency(summary.daily_budget - summary.daily_remaining) : "$0"} spent
              </span>
              <span className="text-muted-foreground">
                {summary ? formatCurrency(summary.daily_budget) : "$0"} limit
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {summary ? formatCurrency(summary.daily_remaining) : "$0"} remaining today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Monthly Budget</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Progress value={monthlyPct} className="h-3" />
            <div className="flex justify-between text-sm">
              <span>
                {summary ? formatCurrency(summary.monthly_budget - summary.monthly_remaining) : "$0"} spent
              </span>
              <span className="text-muted-foreground">
                {summary ? formatCurrency(summary.monthly_budget) : "$0"} limit
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {summary ? formatCurrency(summary.monthly_remaining) : "$0"} remaining
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Daily Trend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Daily Spend (Last 30 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          {dailyUsage.length > 0 ? (
            <DailySpendChart data={dailyUsage} />
          ) : (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground text-sm">
              No usage data available yet
            </div>
          )}
        </CardContent>
      </Card>

      {/* Charts row */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cost by Agent</CardTitle>
          </CardHeader>
          <CardContent>
            {agentCostData.length > 0 ? (
              <AgentCostChart data={agentCostData} />
            ) : (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground text-sm">
                No agent cost data
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cost by Model</CardTitle>
          </CardHeader>
          <CardContent>
            <ModelCostChart data={modelCostData} />
          </CardContent>
        </Card>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-500/15">
                <Zap className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{todayDowngrades}</p>
                <p className="text-xs text-muted-foreground">Downgrades today</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/15">
                <Target className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {forecast ? formatCurrency(forecast.forecast_30d_usd) : "—"}
                </p>
                <p className="text-xs text-muted-foreground">30-day forecast</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/15">
                <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {forecast ? formatCurrency(forecast.daily_average_7d) : "—"}
                </p>
                <p className="text-xs text-muted-foreground">7-day daily avg</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/15">
                {forecast?.trend === "increasing" ? (
                  <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                ) : (
                  <TrendingDown className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                )}
              </div>
              <div>
                <p className="text-2xl font-bold capitalize">
                  {forecast?.trend || "—"}
                </p>
                <p className="text-xs text-muted-foreground">Spend trend</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
