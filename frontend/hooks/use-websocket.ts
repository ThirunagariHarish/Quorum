"use client";

import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { useAgentStore } from "@/stores/agent-store";
import { useTokenStore } from "@/stores/token-store";
import { toast } from "sonner";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useWebSocket() {
  const token = useAuthStore((s) => s.token);
  const updateAgentStatus = useAgentStore((s) => s.updateAgentStatus);
  const updateTokenUsage = useTokenStore((s) => s.updateTokenUsage);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case "agent.status":
            updateAgentStatus(
              data.payload.agent_id,
              data.payload.status,
              data.payload.current_task
            );
            break;
          case "task.progress":
            // Task progress can be handled by specific page components
            break;
          case "paper.created":
            toast.success("New paper generated", {
              description: data.payload.title,
            });
            break;
          case "review.completed":
            toast.info("Review completed", {
              description: `Verdict: ${data.payload.verdict}`,
            });
            break;
          case "token.usage":
            updateTokenUsage(data.payload.agent_id, data.payload.cost);
            break;
          case "budget.alert":
            toast.warning("Budget Alert", {
              description: data.payload.message,
            });
            break;
          case "notification":
            toast(data.payload.title, {
              description: data.payload.message,
            });
            break;
        }
      } catch {
        /* ignore malformed messages */
      }
    },
    [updateAgentStatus, updateTokenUsage]
  );

  useEffect(() => {
    if (!token) return;
    let alive = true;

    const connect = () => {
      const ws = new WebSocket(`${WS_URL}/ws?token=${token}`);
      wsRef.current = ws;

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (alive && reconnectAttempts.current < 5) {
          const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };
    };

    reconnectAttempts.current = 0;
    connect();

    return () => {
      alive = false;
      clearTimeout(reconnectTimeout.current);
      reconnectAttempts.current = 0;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [token, handleMessage]);

  return wsRef;
}
