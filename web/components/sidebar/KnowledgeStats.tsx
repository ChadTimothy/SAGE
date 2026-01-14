"use client";

import type { LucideIcon } from "lucide-react";
import { BarChart3, Award, Target, Calendar } from "lucide-react";
import Link from "next/link";
import type { LearnerStats } from "@/types";

export interface KnowledgeStatsProps {
  stats: LearnerStats;
  collapsed?: boolean;
}

interface StatItem {
  icon: LucideIcon;
  value: number;
  label: string;
}

function StatCard({ icon: Icon, value, label }: StatItem): JSX.Element {
  return (
    <div className="text-center p-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
      <Icon className="h-4 w-4 mx-auto text-sage-500 mb-1" />
      <div className="text-lg font-semibold text-slate-900 dark:text-white">{value}</div>
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
    </div>
  );
}

export function KnowledgeStats({ stats, collapsed }: KnowledgeStatsProps): JSX.Element {
  if (collapsed) {
    return (
      <div className="flex justify-center p-2">
        <BarChart3 className="h-5 w-5 text-sage-600" />
      </div>
    );
  }

  const statItems: StatItem[] = [
    { icon: Award, value: stats.total_proofs, label: "Proofs" },
    { icon: Target, value: stats.completed_goals, label: "Goals" },
    { icon: Calendar, value: stats.total_sessions, label: "Sessions" },
  ];

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
        <BarChart3 className="h-4 w-4 text-sage-600" />
        <span>Your Knowledge</span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {statItems.map((item) => (
          <StatCard key={item.label} {...item} />
        ))}
      </div>

      <Link
        href="/graph"
        className="block text-center text-xs text-sage-600 dark:text-sage-400 hover:underline"
      >
        View Learning Map →
      </Link>
    </div>
  );
}
