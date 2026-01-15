"use client";

/**
 * Divider Primitive - Visual separator with optional label
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface DividerProps extends PrimitiveProps {
  /** Optional text label in the divider */
  label?: string;
  /** Spacing around the divider */
  spacing?: "sm" | "md" | "lg";
  /** Additional CSS classes */
  className?: string;
}

const spacingClasses: Record<string, string> = {
  sm: "my-2",
  md: "my-4",
  lg: "my-6",
};

export function Divider({
  label,
  spacing = "md",
  className,
}: DividerProps): React.ReactElement {
  if (label) {
    return (
      <div
        className={cn(
          "flex items-center",
          spacingClasses[spacing],
          className
        )}
      >
        <div className="flex-1 border-t border-slate-200 dark:border-slate-700" />
        <span className="px-3 text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          {label}
        </span>
        <div className="flex-1 border-t border-slate-200 dark:border-slate-700" />
      </div>
    );
  }

  return (
    <hr
      className={cn(
        "border-slate-200 dark:border-slate-700",
        spacingClasses[spacing],
        className
      )}
    />
  );
}
