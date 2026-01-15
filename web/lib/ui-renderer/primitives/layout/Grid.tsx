"use client";

/**
 * Grid Primitive - Grid layout with configurable columns
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface GridProps extends PrimitiveProps {
  /** Number of columns (1-4) */
  columns?: 1 | 2 | 3 | 4;
  /** Gap between items (Tailwind spacing scale) */
  gap?: number;
  /** Additional CSS classes */
  className?: string;
}

const columnClasses: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
  4: "grid-cols-4",
};

const gapClasses: Record<number, string> = {
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
  5: "gap-5",
  6: "gap-6",
  8: "gap-8",
};

export function Grid({
  columns = 2,
  gap = 4,
  className,
  children,
}: GridProps): React.ReactElement {
  return (
    <div
      className={cn(
        "grid",
        columnClasses[columns] || "grid-cols-2",
        gapClasses[gap] || "gap-4",
        className
      )}
    >
      {children}
    </div>
  );
}
