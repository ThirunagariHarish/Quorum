"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatTokens } from "@/lib/utils";
import { Bot } from "lucide-react";

interface AgentStatusCardProps {
  name: string;
  status: string;
  currentTask?: string | null;
  totalTokens: number;
  compact?: boolean;
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  active: "default",
  working: "default",
  idle: "secondary",
  error: "destructive",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/25",
  working: "bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/25",
  idle: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400 border-zinc-500/25",
  error: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/25",
};

export function AgentStatusCard({
  name,
  status,
  currentTask,
  totalTokens,
  compact,
}: AgentStatusCardProps) {
  const statusColor = STATUS_COLORS[status] || STATUS_COLORS.idle;

  return (
    <Card className={compact ? "p-4" : ""}>
      <CardHeader className={compact ? "p-0 pb-3" : ""}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm font-semibold">{name}</CardTitle>
          </div>
          <Badge variant={STATUS_VARIANT[status] || "secondary"} className={statusColor}>
            {status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className={compact ? "p-0" : ""}>
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground truncate">
            {currentTask || "No active task"}
          </p>
          <p className="text-xs font-medium">
            {formatTokens(totalTokens)} tokens used
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
