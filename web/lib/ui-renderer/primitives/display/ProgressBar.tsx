"use client";

/**
 * ProgressBar Primitive - Visual progress indicator
 */

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface ProgressBarProps extends PrimitiveProps {
  /** Current progress value */
  value: number;
  /** Maximum value */
  max?: number;
  /** Optional label */
  label?: string;
  /** Show percentage text */
  showPercentage?: boolean;
  /** Color variant */
  color?: "default" | "success" | "warning";
  /** Additional CSS classes */
  className?: string;
}

const colorClasses: Record<string, string> = {
  default: "bg-sage-600 dark:bg-sage-500",
  success: "bg-emerald-600 dark:bg-emerald-500",
  warning: "bg-amber-600 dark:bg-amber-500",
};

export function ProgressBar({
  value,
  max = 100,
  label,
  showPercentage = false,
  color = "default",
  className,
}: ProgressBarProps): React.ReactElement {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div className={cn("space-y-1.5", className)}>
      {(label || showPercentage) && (
        <div className="flex justify-between items-center text-sm">
          {label && (
            <span className="text-slate-700 dark:text-slate-300">{label}</span>
          )}
          {showPercentage && (
            <span className="text-slate-500 dark:text-slate-400">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}
      <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          className={cn("h-full rounded-full", colorClasses[color])}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}
