import { create } from "zustand";
import { persist } from "zustand/middleware";
import api from "@/lib/api";

interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

interface AuthState {
  token: string | null;
  refreshTokenValue: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  setup: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  fetchUser: () => Promise<void>;
  setToken: (token: string, refreshToken: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshTokenValue: null,
      user: null,
      isAuthenticated: false,

      setToken: (token, refreshToken) => {
        api.setToken(token);
        set({ token, refreshTokenValue: refreshToken, isAuthenticated: true });
      },

      login: async (email, password) => {
        const res = await api.login(email, password);
        api.setToken(res.access_token);
        set({
          token: res.access_token,
          refreshTokenValue: res.refresh_token,
          isAuthenticated: true,
        });
        await get().fetchUser();
      },

      setup: async (email, password, displayName) => {
        const res = await api.setup(email, password, displayName);
        api.setToken(res.access_token);
        set({
          token: res.access_token,
          refreshTokenValue: res.refresh_token,
          isAuthenticated: true,
        });
        await get().fetchUser();
      },

      logout: () => {
        api.setToken(null);
        set({
          token: null,
          refreshTokenValue: null,
          user: null,
          isAuthenticated: false,
        });
      },

      refreshToken: async () => {
        const rt = get().refreshTokenValue;
        if (!rt) throw new Error("No refresh token");
        const res = await api.refreshToken(rt);
        api.setToken(res.access_token);
        set({ token: res.access_token, isAuthenticated: true });
      },

      fetchUser: async () => {
        const user = await api.getMe();
        set({ user });
      },
    }),
    {
      name: "quorum-auth",
      partialize: (state) => ({
        token: state.token,
        refreshTokenValue: state.refreshTokenValue,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          api.setToken(state.token);
        }
      },
    }
  )
);
