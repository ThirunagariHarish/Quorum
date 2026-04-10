"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import api, { type Agent, type AgentTask } from "@/lib/api";
import { formatDate, formatTokens, formatCurrency } from "@/lib/utils";
import { ArrowLeft, Bot, Loader2, Send } from "lucide-react";
import { toast } from "sonner";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/15 text-green-700 dark:text-green-400",
  working: "bg-green-500/15 text-green-700 dark:text-green-400",
  idle: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400",
  error: "bg-red-500/15 text-red-700 dark:text-red-400",
  completed: "bg-green-500/15 text-green-700 dark:text-green-400",
  queued: "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400",
  running: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
  cancelled: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400",
};

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params.id as string;

  const [agent, setAgent] = useState<Agent | null>(null);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [topic, setTopic] = useState("");
  const [contentType, setContentType] = useState("ieee_full");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([api.getAgent(agentId), api.getAgentTasks(agentId)])
      .then(([agentData, taskData]) => {
        setAgent(agentData);
        setTasks(Array.isArray(taskData) ? taskData : taskData.items ?? []);
      })
      .finally(() => setLoading(false));
  }, [agentId]);

  const handleAssignTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setSubmitting(true);
    try {
      const task = await api.createAgentTask(agentId, {
        topic,
        content_type: contentType,
      });
      setTasks((prev) => [task, ...prev]);
      setTopic("");
      toast.success("Task assigned successfully");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to assign task");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Agent not found</p>
      </div>
    );
  }

  const currentTasks = tasks.filter((t) => ["queued", "running"].includes(t.status));
  const completedTasks = tasks.filter((t) => t.status === "completed");

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex items-center gap-3 flex-1">
          <Bot className="h-6 w-6 text-muted-foreground" />
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{agent.name}</h2>
            <p className="text-sm text-muted-foreground">
              {agent.agent_type} &middot; {agent.default_model} &middot;{" "}
              {formatTokens(agent.total_tokens_used)} tokens &middot;{" "}
              {formatCurrency(agent.total_cost_usd)}
            </p>
          </div>
          <Badge
            variant="secondary"
            className={`ml-auto ${STATUS_COLORS[agent.status] || ""}`}
          >
            {agent.status}
          </Badge>
        </div>
      </div>

      <Tabs defaultValue="current">
        <TabsList>
          <TabsTrigger value="current">Current Tasks</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="current" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {currentTasks.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Task</TableHead>
                      <TableHead className="w-28">Phase</TableHead>
                      <TableHead className="w-28">Model</TableHead>
                      <TableHead className="w-28">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currentTasks.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell className="font-medium">{task.topic}</TableCell>
                        <TableCell>{task.phase || "—"}</TableCell>
                        <TableCell className="text-xs">{task.model || "—"}</TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className={STATUS_COLORS[task.status] || ""}
                          >
                            {task.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No active tasks
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {completedTasks.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Task</TableHead>
                      <TableHead className="w-28">Type</TableHead>
                      <TableHead className="w-36">Completed</TableHead>
                      <TableHead className="w-28">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {completedTasks.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell className="font-medium">{task.topic}</TableCell>
                        <TableCell>{task.content_type}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {task.completed_at ? formatDate(task.completed_at) : "—"}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className={STATUS_COLORS[task.status] || ""}
                          >
                            {task.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No completed tasks
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Manual Task Assignment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Assign New Task</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAssignTask} className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 space-y-1">
              <Label htmlFor="topic" className="sr-only">Topic</Label>
              <Input
                id="topic"
                placeholder="Enter research topic..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
              />
            </div>
            <div className="w-full sm:w-48 space-y-1">
              <Label htmlFor="contentType" className="sr-only">Content Type</Label>
              <Select value={contentType} onValueChange={(v) => v && setContentType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ieee_full">IEEE Full Paper</SelectItem>
                  <SelectItem value="ieee_short">IEEE Short Paper</SelectItem>
                  <SelectItem value="workshop">Workshop Paper</SelectItem>
                  <SelectItem value="poster">Poster</SelectItem>
                  <SelectItem value="blog">Blog Post</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={submitting || !topic.trim()}>
              {submitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              Assign
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
