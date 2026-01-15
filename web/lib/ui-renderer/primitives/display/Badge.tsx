"use client";

/**
 * Badge Primitive - Small status indicator
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface BadgeProps extends PrimitiveProps {
  /** Badge label text */
  label: string;
  /** Badge variant */
  variant?: "default" | "success" | "warning" | "error" | "info";
  /** Additional CSS classes */
  className?: string;
}

const variantClasses: Record<string, string> = {
  default: "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300",
  success:
    "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300",
  warning:
    "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300",
  error: "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300",
  info: "bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300",
};

export function Badge({
  label,
  variant = "default",
  className,
}: BadgeProps): React.ReactElement {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5",
        "text-xs font-medium rounded-full",
        variantClasses[variant],
        className
      )}
    >
      {label}
    </span>
  );
}
