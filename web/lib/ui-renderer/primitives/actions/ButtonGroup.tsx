"use client";

/**
 * ButtonGroup Primitive - Horizontal button arrangement
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface ButtonGroupProps extends PrimitiveProps {
  /** Alignment of buttons */
  align?: "start" | "center" | "end" | "stretch";
  /** Gap between buttons */
  gap?: number;
  /** Additional CSS classes */
  className?: string;
}

const alignClasses: Record<string, string> = {
  start: "justify-start",
  center: "justify-center",
  end: "justify-end",
  stretch: "justify-stretch",
};

const gapClasses: Record<number, string> = {
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
};

export function ButtonGroup({
  align = "end",
  gap = 3,
  className,
  children,
}: ButtonGroupProps): React.ReactElement {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center",
        alignClasses[align],
        gapClasses[gap] || "gap-3",
        className
      )}
    >
      {children}
    </div>
  );
}
