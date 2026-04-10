"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAgentStore } from "@/stores/agent-store";
import { formatTokens, formatCurrency, formatDate } from "@/lib/utils";
import { Bot, RefreshCw } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/25",
  working: "bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/25",
  idle: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400 border-zinc-500/25",
  error: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/25",
};

export default function AgentsPage() {
  const { agents, loading, fetchAgents } = useAgentStore();

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Agents</h2>
          <p className="text-muted-foreground">Monitor and manage your research agents</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchAgents()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {loading
          ? Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-40" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-9 w-full" />
                </CardContent>
              </Card>
            ))
          : agents.map((agent) => (
              <Card key={agent.id} className="flex flex-col">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Bot className="h-5 w-5 text-muted-foreground" />
                      <CardTitle className="text-base">{agent.name}</CardTitle>
                    </div>
                    <Badge
                      variant="secondary"
                      className={STATUS_COLORS[agent.status] || STATUS_COLORS.idle}
                    >
                      {agent.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex flex-col flex-1 space-y-3">
                  <div className="space-y-1 text-sm flex-1">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Type</span>
                      <span className="font-medium">{agent.agent_type}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Tokens</span>
                      <span className="font-medium">{formatTokens(agent.total_tokens_used)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Cost</span>
                      <span className="font-medium">{formatCurrency(agent.total_cost_usd)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Last active</span>
                      <span className="font-medium text-xs">
                        {agent.last_active_at
                          ? formatDate(agent.last_active_at, { month: "short", day: "numeric", hour: "numeric", minute: "numeric" })
                          : "Never"}
                      </span>
                    </div>
                  </div>
                  <Link href={`/agents/${agent.id}`}>
                    <Button variant="outline" className="w-full" size="sm">
                      View Details
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
      </div>

      {!loading && agents.length === 0 && (
        <div className="text-center py-12">
          <Bot className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No agents found</h3>
          <p className="text-muted-foreground">Agents will appear here once the backend is running.</p>
        </div>
      )}
    </div>
  );
}
