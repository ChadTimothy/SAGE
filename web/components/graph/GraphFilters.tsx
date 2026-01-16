"use client";

import { Filter, Target, BookOpen, Award, Eye, Network } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GraphFilterState, OutcomeSnapshot } from "@/types";

export interface GraphFiltersProps {
  filters: GraphFilterState;
  outcomes: OutcomeSnapshot[];
  onFilterChange: (filters: GraphFilterState) => void;
  /** Whether to show labels on all nodes */
  showLabels?: boolean;
  onShowLabelsChange?: (show: boolean) => void;
  /** Connection depth limit (0 = all, 1-3 = limited) */
  depthLimit?: number;
  onDepthLimitChange?: (depth: number) => void;
}

export function GraphFilters({
  filters,
  outcomes,
  onFilterChange,
  showLabels = true,
  onShowLabelsChange,
  depthLimit = 0,
  onDepthLimitChange,
}: GraphFiltersProps): JSX.Element {
  const handleOutcomeChange = (outcomeId: string | null) => {
    onFilterChange({ ...filters, selectedOutcome: outcomeId });
  };

  const handleToggle = (key: keyof GraphFilterState) => {
    if (key === "selectedOutcome") return;
    onFilterChange({ ...filters, [key]: !filters[key] });
  };

  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
        <Filter className="h-4 w-4" />
        <span>Filters</span>
      </div>

      <div className="h-4 w-px bg-slate-200 dark:bg-slate-700" />

      <select
        value={filters.selectedOutcome || ""}
        onChange={(e) => handleOutcomeChange(e.target.value || null)}
        className="px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-sage-500"
      >
        <option value="">All Goals</option>
        {outcomes.map((outcome) => (
          <option key={outcome.id} value={outcome.id}>
            {outcome.description}
          </option>
        ))}
      </select>

      <div className="h-4 w-px bg-slate-200 dark:bg-slate-700" />

      <button
        onClick={() => handleToggle("showOutcomes")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors",
          filters.showOutcomes
            ? "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400"
            : "bg-slate-100 text-slate-500 dark:bg-slate-900 dark:text-slate-500"
        )}
      >
        <Target className="h-3.5 w-3.5" />
        Goals
      </button>

      <button
        onClick={() => handleToggle("showConcepts")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors",
          filters.showConcepts
            ? "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
            : "bg-slate-100 text-slate-500 dark:bg-slate-900 dark:text-slate-500"
        )}
      >
        <BookOpen className="h-3.5 w-3.5" />
        Concepts
      </button>

      <button
        onClick={() => handleToggle("showProvenOnly")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors",
          filters.showProvenOnly
            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
            : "bg-slate-100 text-slate-500 dark:bg-slate-900 dark:text-slate-500"
        )}
      >
        <Award className="h-3.5 w-3.5" />
        Proven Only
      </button>

      {/* New Obsidian-style controls */}
      <div className="h-4 w-px bg-slate-200 dark:bg-slate-700" />

      {onShowLabelsChange && (
        <button
          onClick={() => onShowLabelsChange(!showLabels)}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors",
            showLabels
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
              : "bg-slate-100 text-slate-500 dark:bg-slate-900 dark:text-slate-500"
          )}
          title={showLabels ? "Hide labels (show on hover)" : "Show all labels"}
        >
          <Eye className="h-3.5 w-3.5" />
          Labels
        </button>
      )}

      {onDepthLimitChange && (
        <div className="flex items-center gap-1.5">
          <Network className="h-3.5 w-3.5 text-slate-500" />
          <select
            value={depthLimit}
            onChange={(e) => onDepthLimitChange(Number(e.target.value))}
            className="px-2 py-1 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-sage-500"
            title="Connection depth on hover"
          >
            <option value={0}>All connections</option>
            <option value={1}>Direct only</option>
            <option value={2}>2nd degree</option>
            <option value={3}>3rd degree</option>
          </select>
        </div>
      )}
    </div>
  );
}
