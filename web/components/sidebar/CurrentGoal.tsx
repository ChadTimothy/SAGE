"use client";

import { Target, Check, Circle, Loader2, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OutcomeSnapshot, ConceptSnapshot } from "@/types";

export interface CurrentGoalProps {
  outcome: OutcomeSnapshot | null;
  collapsed?: boolean;
}

function getStatusIcon(status: ConceptSnapshot["status"]): JSX.Element {
  switch (status) {
    case "proven":
      return <Check className="h-3 w-3 text-sage-500" />;
    case "in_progress":
      return <Loader2 className="h-3 w-3 text-yellow-500 animate-spin" />;
    case "identified":
    default:
      return <Circle className="h-3 w-3 text-slate-400" />;
  }
}

function getOutcomeStatusLabel(status: OutcomeSnapshot["status"]): string {
  switch (status) {
    case "achieved":
      return "You can do this!";
    case "paused":
      return "Paused";
    case "abandoned":
      return "Set aside";
    case "active":
    default:
      return "Working toward";
  }
}

export function CurrentGoal({ outcome, collapsed }: CurrentGoalProps): JSX.Element {
  if (collapsed) {
    return (
      <div className="flex justify-center p-2">
        <Target className="h-5 w-5 text-sage-600" />
      </div>
    );
  }

  if (!outcome) {
    return (
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
          <Target className="h-4 w-4 text-sage-600" />
          <span>Current Goal</span>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 italic">
          No active goal. Start a conversation to set one.
        </p>
      </div>
    );
  }

  const isAchieved = outcome.status === "achieved";

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
          {isAchieved ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : (
            <Target className="h-4 w-4 text-sage-600" />
          )}
          <span>Current Goal</span>
        </div>
        <span className={cn(
          "text-xs font-medium px-2 py-0.5 rounded-full",
          isAchieved
            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
            : "bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-400"
        )}>
          {getOutcomeStatusLabel(outcome.status)}
        </span>
      </div>

      <p className="text-sm text-slate-900 dark:text-white font-medium">
        {outcome.description}
      </p>

      {outcome.concepts.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Areas explored:
          </p>
          <ul className="space-y-1">
            {outcome.concepts.slice(0, 5).map((concept) => (
              <li
                key={concept.id}
                className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400"
              >
                {getStatusIcon(concept.status)}
                <span>{concept.display_name}</span>
              </li>
            ))}
            {outcome.concepts.length > 5 && (
              <li className="text-xs text-slate-400 dark:text-slate-500 pl-5">
                +{outcome.concepts.length - 5} more
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
