"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import {
  LayoutDashboard,
  Bot,
  FileText,
  ClipboardCheck,
  Coins,
  Calendar,
  Settings,
  PanelLeftClose,
  PanelLeft,
  Menu,
  FileCode2,
} from "lucide-react";
import { useState } from "react";

const NAV_ITEMS = [
  { label: "Home", href: "/dashboard", icon: LayoutDashboard },
  { label: "Agents", href: "/agents", icon: Bot },
  { label: "Files", href: "/files", icon: FileText },
  { label: "Review", href: "/review", icon: ClipboardCheck },
  { label: "LaTeX Editor", href: "/latex-editor", icon: FileCode2 },
  { label: "Token Usage", href: "/tokens", icon: Coins },
  { label: "Deadlines", href: "/deadlines", icon: Calendar },
  { label: "Settings", href: "/settings", icon: Settings },
];

function NavContent({ collapsed, onSelect }: { collapsed: boolean; onSelect?: () => void }) {
  const pathname = usePathname();

  return (
    <ScrollArea className="flex-1 py-2">
      <nav className="flex flex-col gap-1 px-2">
        {NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link key={item.href} href={item.href} onClick={onSelect}>
              <span
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  "hover:bg-accent hover:text-accent-foreground",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground",
                  collapsed && "justify-center px-2"
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </span>
            </Link>
          );
        })}
      </nav>
    </ScrollArea>
  );
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden md:flex flex-col border-r bg-card transition-all duration-200",
          collapsed ? "w-16" : "w-56"
        )}
      >
        <div className="flex items-center justify-end p-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <PanelLeft className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </Button>
        </div>
        <NavContent collapsed={collapsed} />
      </aside>

      {/* Mobile sidebar */}
      <Sheet>
        <SheetTrigger
          render={
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden fixed left-4 top-3 z-40"
            />
          }
        >
          <Menu className="h-5 w-5" />
        </SheetTrigger>
        <SheetContent side="left" className="w-56 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="flex items-center gap-2 border-b px-4 py-3">
            <Bot className="h-6 w-6 text-primary" />
            <span className="font-bold text-lg">Quorum</span>
          </div>
          <NavContent collapsed={false} />
        </SheetContent>
      </Sheet>
    </>
  );
}
