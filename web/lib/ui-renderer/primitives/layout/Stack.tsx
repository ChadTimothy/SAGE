"use client";

/**
 * Stack Primitive - Vertical or horizontal arrangement of children
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface StackProps extends PrimitiveProps {
  /** Stack direction */
  direction?: "vertical" | "horizontal";
  /** Gap between children (Tailwind spacing scale 1-12) */
  gap?: number;
  /** Alignment of children */
  align?: "start" | "center" | "end" | "stretch";
  /** Justify content */
  justify?: "start" | "center" | "end" | "between" | "around";
  /** Additional CSS classes */
  className?: string;
}

const gapClasses: Record<number, string> = {
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
  5: "gap-5",
  6: "gap-6",
  8: "gap-8",
  10: "gap-10",
  12: "gap-12",
};

const alignClasses: Record<string, string> = {
  start: "items-start",
  center: "items-center",
  end: "items-end",
  stretch: "items-stretch",
};

const justifyClasses: Record<string, string> = {
  start: "justify-start",
  center: "justify-center",
  end: "justify-end",
  between: "justify-between",
  around: "justify-around",
};

export function Stack({
  direction = "vertical",
  gap = 4,
  align = "stretch",
  justify = "start",
  className,
  children,
}: StackProps): React.ReactElement {
  return (
    <div
      className={cn(
        "flex",
        direction === "vertical" ? "flex-col" : "flex-row",
        gapClasses[gap] || "gap-4",
        alignClasses[align],
        justifyClasses[justify],
        className
      )}
    >
      {children}
    </div>
  );
}
