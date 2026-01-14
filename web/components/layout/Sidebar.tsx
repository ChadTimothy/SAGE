"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Network,
  Target,
  Award,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  CurrentGoal,
  KnowledgeStats,
  UpcomingApplications,
} from "@/components/sidebar";
import type {
  OutcomeSnapshot,
  LearnerStats,
  ApplicationSnapshot,
} from "@/types";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { href: "/chat", label: "Chat", icon: <MessageSquare className="h-5 w-5" /> },
  { href: "/graph", label: "Knowledge Graph", icon: <Network className="h-5 w-5" /> },
];

const secondaryItems: NavItem[] = [
  { href: "/goals", label: "Goals", icon: <Target className="h-5 w-5" /> },
  { href: "/proofs", label: "Proofs", icon: <Award className="h-5 w-5" /> },
  { href: "/settings", label: "Settings", icon: <Settings className="h-5 w-5" /> },
];

interface NavLinkProps {
  item: NavItem;
  isActive: boolean;
  collapsed: boolean;
}

function NavLink({ item, isActive, collapsed }: NavLinkProps): JSX.Element {
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
        isActive
          ? "bg-sage-100 text-sage-700 dark:bg-sage-900 dark:text-sage-300"
          : "hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
      )}
    >
      {item.icon}
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}

export interface SidebarProps {
  outcome?: OutcomeSnapshot | null;
  stats?: LearnerStats;
  applications?: ApplicationSnapshot[];
}

const defaultStats: LearnerStats = {
  total_proofs: 0,
  completed_goals: 0,
  total_sessions: 0,
};

export function Sidebar({
  outcome = null,
  stats = defaultStats,
  applications = [],
}: SidebarProps): JSX.Element {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-slate-50 dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transition-all duration-300",
        collapsed ? "w-16" : "w-72"
      )}
    >
      <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-800">
        {!collapsed && (
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-sage-600">SAGE</span>
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="p-2 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            isActive={pathname === item.href}
            collapsed={collapsed}
          />
        ))}
      </nav>

      <div className="flex-1 overflow-y-auto border-t border-slate-200 dark:border-slate-800 divide-y divide-slate-200 dark:divide-slate-800">
        <CurrentGoal outcome={outcome} collapsed={collapsed} />
        <KnowledgeStats stats={stats} collapsed={collapsed} />
        <UpcomingApplications applications={applications} collapsed={collapsed} />
      </div>

      <div className="p-2 border-t border-slate-200 dark:border-slate-800 space-y-1">
        {secondaryItems.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            isActive={pathname === item.href}
            collapsed={collapsed}
          />
        ))}
      </div>
    </aside>
  );
}
