"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AgentStatusCard } from "@/components/agents/agent-status-card";
import { useAgentStore } from "@/stores/agent-store";
import { useTokenStore } from "@/stores/token-store";
import { useAuthStore } from "@/stores/auth-store";
import api, { type Paper } from "@/lib/api";
import { formatDate, formatCurrency } from "@/lib/utils";
import { FileText, Activity } from "lucide-react";
import Link from "next/link";

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400",
  in_review: "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400",
  approved: "bg-green-500/15 text-green-700 dark:text-green-400",
  rejected: "bg-red-500/15 text-red-700 dark:text-red-400",
  published: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
};

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { agents, fetchAgents, loading: agentsLoading } = useAgentStore();
  const { budget, fetchBudget } = useTokenStore();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [papersLoading, setPapersLoading] = useState(true);

  useEffect(() => {
    fetchAgents();
    fetchBudget();
    api
      .getPapers({ per_page: "5", sort_by: "created_at", sort_order: "desc" })
      .then((res) => setPapers(res.items))
      .finally(() => setPapersLoading(false));
  }, [fetchAgents, fetchBudget]);

  const displayAgents = agents.slice(0, 3);
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const dailyPct = budget && budget.daily_limit_usd
    ? Math.round(((budget.daily_limit_usd - budget.daily_spent) / budget.daily_limit_usd) * 100)
    : 0;
  const monthlyPct = budget && budget.monthly_limit_usd
    ? Math.round(
        ((budget.monthly_limit_usd - budget.monthly_spent) / budget.monthly_limit_usd) * 100
      )
    : 0;

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          Welcome back{user?.display_name ? `, ${user.display_name.split(" ")[0]}` : ""}
        </h2>
        <p className="text-muted-foreground">{today}</p>
      </div>

      {/* Agent Status Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {agentsLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-3 w-20" />
                </CardContent>
              </Card>
            ))
          : displayAgents.map((agent) => (
              <AgentStatusCard
                key={agent.id}
                name={agent.name}
                status={agent.status}
                currentTask={agent.current_task?.topic}
                totalTokens={agent.total_tokens_used}
              />
            ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Papers */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Recent Papers
            </CardTitle>
            <Link
              href="/files"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {papersLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead className="w-24">Type</TableHead>
                    <TableHead className="w-28">Status</TableHead>
                    <TableHead className="w-28 text-right">Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {papers.map((paper) => (
                    <TableRow key={paper.id}>
                      <TableCell className="font-medium truncate max-w-[300px]">
                        {paper.title}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {paper.paper_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={STATUS_BADGE[paper.status] || ""}
                        >
                          {paper.status.replace("_", " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground">
                        {formatDate(paper.created_at, { month: "short", day: "numeric" })}
                      </TableCell>
                    </TableRow>
                  ))}
                  {papers.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                        No papers yet. Agents will generate papers on their schedule.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Budget */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Daily Budget</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {budget ? (
                <>
                  <div className="flex justify-between text-sm">
                    <span>{formatCurrency(budget.daily_spent)} spent</span>
                    <span className="text-muted-foreground">
                      {formatCurrency(budget.daily_limit_usd)} limit
                    </span>
                  </div>
                  <Progress value={100 - dailyPct} className="h-2" />
                  <p className="text-xs text-muted-foreground">
                    {formatCurrency(budget.daily_limit_usd - budget.daily_spent)} remaining today
                  </p>
                </>
              ) : (
                <Skeleton className="h-16 w-full" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Monthly Budget</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {budget ? (
                <>
                  <div className="flex justify-between text-sm">
                    <span>{formatCurrency(budget.monthly_spent)} spent</span>
                    <span className="text-muted-foreground">
                      {formatCurrency(budget.monthly_limit_usd)} limit
                    </span>
                  </div>
                  <Progress value={100 - monthlyPct} className="h-2" />
                  <p className="text-xs text-muted-foreground">
                    {formatCurrency(budget.monthly_limit_usd - budget.monthly_spent)} remaining
                  </p>
                </>
              ) : (
                <Skeleton className="h-16 w-full" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Activity feed updates in real-time via WebSocket.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
