"use client";

/**
 * Card Primitive - Contained section with optional title
 */

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { cardVariants } from "../../animations";
import type { PrimitiveProps } from "../../types";

interface CardProps extends PrimitiveProps {
  /** Optional card title */
  title?: string;
  /** Card variant */
  variant?: "default" | "highlight" | "warning" | "success";
  /** Padding size */
  padding?: "sm" | "md" | "lg";
  /** Additional CSS classes */
  className?: string;
}

const variantClasses: Record<string, string> = {
  default:
    "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700",
  highlight:
    "bg-sage-50 dark:bg-sage-950 border-sage-200 dark:border-sage-800",
  warning:
    "bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800",
  success:
    "bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800",
};

const paddingClasses: Record<string, string> = {
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

export function Card({
  title,
  variant = "default",
  padding = "md",
  className,
  children,
}: CardProps): React.ReactElement {
  return (
    <motion.div
      className={cn(
        "rounded-lg border shadow-sm",
        variantClasses[variant],
        paddingClasses[padding],
        className
      )}
      variants={cardVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {title && (
        <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
          {title}
        </h3>
      )}
      {children}
    </motion.div>
  );
}
