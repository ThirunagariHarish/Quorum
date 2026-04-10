"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { AppShell } from "@/components/layout/app-shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, token } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated || !token) {
      router.push("/login");
    }
  }, [isAuthenticated, token, router]);

  if (!isAuthenticated || !token) return null;

  return <AppShell>{children}</AppShell>;
}
