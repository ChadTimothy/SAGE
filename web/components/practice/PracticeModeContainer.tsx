"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { X, Theater, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PracticeScenario {
  id: string;
  title: string;
  description: string;
  sageRole: string;
  userRole: string;
}

export interface PracticeModeContainerProps {
  isActive: boolean;
  isLoading?: boolean;
  scenario: PracticeScenario | null;
  onEnd: () => void;
  onHint: () => void;
  children: ReactNode;
  className?: string;
}

export function PracticeModeContainer({
  isActive,
  isLoading = false,
  scenario,
  onEnd,
  onHint,
  children,
  className,
}: PracticeModeContainerProps): JSX.Element {
  if (!isActive || !scenario) {
    return <>{children}</>;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className={cn(
        "flex flex-col h-full",
        "bg-gradient-to-b from-amber-50/50 to-transparent dark:from-amber-900/10 dark:to-transparent",
        className
      )}
    >
      {/* Practice Mode Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-100/50 dark:bg-amber-900/20">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-200 dark:bg-amber-800">
            <Theater className="w-4 h-4 text-amber-700 dark:text-amber-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-amber-800 dark:text-amber-200">
                PRACTICE MODE
              </span>
            </div>
            <p className="text-xs text-amber-600 dark:text-amber-400">
              {scenario.title} • SAGE is playing: {scenario.sageRole}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onHint}
            disabled={isLoading}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm",
              "bg-amber-200/50 dark:bg-amber-800/50",
              "text-amber-700 dark:text-amber-300",
              "hover:bg-amber-200 dark:hover:bg-amber-800",
              "transition-colors",
              isLoading && "opacity-50 cursor-not-allowed"
            )}
          >
            <Lightbulb className="w-4 h-4" />
            <span>Hint</span>
          </button>

          <button
            onClick={onEnd}
            disabled={isLoading}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm",
              "bg-slate-200/50 dark:bg-slate-700/50",
              "text-slate-700 dark:text-slate-300",
              "hover:bg-slate-200 dark:hover:bg-slate-700",
              "transition-colors",
              isLoading && "opacity-50 cursor-not-allowed"
            )}
          >
            <X className="w-4 h-4" />
            <span>End Practice</span>
          </button>
        </div>
      </div>

      {/* Practice Content */}
      <div className="flex-1 overflow-hidden">{children}</div>
    </motion.div>
  );
}
