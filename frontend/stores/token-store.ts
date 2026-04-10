import { create } from "zustand";
import api, { type BudgetConfig, type TokenUsageResponse } from "@/lib/api";

interface TokenState {
  budget: BudgetConfig | null;
  dailyUsage: TokenUsageResponse["data"];
  agentUsage: Record<string, number>;
  summary: TokenUsageResponse["summary"] | null;
  forecast: { forecast_30d_usd: number; daily_average_7d: number; trend: string; projected_monthly: number } | null;
  loading: boolean;
  fetchUsage: (params?: Record<string, string>) => Promise<void>;
  fetchBudget: () => Promise<void>;
  fetchForecast: () => Promise<void>;
  updateTokenUsage: (agentId: string, cost: number) => void;
}

export const useTokenStore = create<TokenState>((set, get) => ({
  budget: null,
  dailyUsage: [],
  agentUsage: {},
  summary: null,
  forecast: null,
  loading: false,

  fetchUsage: async (params) => {
    set({ loading: true });
    try {
      const res = await api.getTokenUsage(params);
      set({ dailyUsage: res.data, summary: res.summary, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchBudget: async () => {
    try {
      const budget = await api.getBudget();
      set({ budget });
    } catch {
      /* empty */
    }
  },

  fetchForecast: async () => {
    try {
      const forecast = await api.getForecast();
      set({ forecast });
    } catch {
      /* empty */
    }
  },

  updateTokenUsage: (agentId, cost) => {
    const current = get().agentUsage;
    set({ agentUsage: { ...current, [agentId]: (current[agentId] || 0) + cost } });
  },
}));
