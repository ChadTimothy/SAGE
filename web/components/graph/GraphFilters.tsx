"use client";

import { Filter, Target, BookOpen, Award } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GraphFilterState, OutcomeSnapshot } from "@/types";

export interface GraphFiltersProps {
  filters: GraphFilterState;
  outcomes: OutcomeSnapshot[];
  onFilterChange: (filters: GraphFilterState) => void;
}

export function GraphFilters({
  filters,
  outcomes,
  onFilterChange,
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
            ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
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
            ? "bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-400"
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
    </div>
  );
}
