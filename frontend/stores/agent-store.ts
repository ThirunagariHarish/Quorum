import { create } from "zustand";
import api, { type Agent } from "@/lib/api";

interface AgentState {
  agents: Agent[];
  activeAgent: Agent | null;
  loading: boolean;
  fetchAgents: () => Promise<void>;
  setActiveAgent: (agent: Agent | null) => void;
  updateAgentStatus: (agentId: string, status: string, currentTask?: string) => void;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  activeAgent: null,
  loading: false,

  fetchAgents: async () => {
    set({ loading: true });
    try {
      const res = await api.getAgents();
      set({ agents: res.items, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  setActiveAgent: (agent) => set({ activeAgent: agent }),

  updateAgentStatus: (agentId, status, currentTask) => {
    const agents = get().agents.map((a) =>
      a.id === agentId
        ? {
            ...a,
            status,
            current_task: currentTask
              ? { ...a.current_task!, topic: currentTask, phase: status }
              : a.current_task,
          }
        : a
    );
    set({ agents });
  },
}));
