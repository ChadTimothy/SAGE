"use client";

/**
 * Text Primitive - Basic text display with variants
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface TextProps extends PrimitiveProps {
  /** Text content to display */
  content: string;
  /** Text variant */
  variant?: "heading" | "subheading" | "body" | "caption" | "label";
  /** Text color */
  color?: "default" | "muted" | "accent" | "success" | "warning" | "error";
  /** Text alignment */
  align?: "left" | "center" | "right";
  /** Additional CSS classes */
  className?: string;
}

const variantClasses: Record<string, string> = {
  heading: "text-lg font-semibold",
  subheading: "text-base font-medium",
  body: "text-sm",
  caption: "text-xs",
  label: "text-xs font-medium uppercase tracking-wider",
};

const colorClasses: Record<string, string> = {
  default: "text-slate-900 dark:text-slate-100",
  muted: "text-slate-500 dark:text-slate-400",
  accent: "text-sage-600 dark:text-sage-400",
  success: "text-emerald-600 dark:text-emerald-400",
  warning: "text-amber-600 dark:text-amber-400",
  error: "text-red-600 dark:text-red-400",
};

const alignClasses: Record<string, string> = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

export function Text({
  content,
  variant = "body",
  color = "default",
  align = "left",
  className,
}: TextProps): React.ReactElement {
  const Tag = variant === "heading" ? "h2" : variant === "subheading" ? "h3" : "p";

  return (
    <Tag
      className={cn(
        variantClasses[variant],
        colorClasses[color],
        alignClasses[align],
        className
      )}
    >
      {content}
    </Tag>
  );
}
