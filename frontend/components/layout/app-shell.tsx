"use client";

import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { useWebSocket } from "@/hooks/use-websocket";

export function AppShell({ children }: { children: React.ReactNode }) {
  useWebSocket();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
