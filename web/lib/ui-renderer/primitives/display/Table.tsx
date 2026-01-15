"use client";

/**
 * Table Primitive - Data table display
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface TableColumn {
  key: string;
  header: string;
}

interface TableProps extends PrimitiveProps {
  /** Column definitions */
  columns: TableColumn[];
  /** Row data */
  rows: Array<Record<string, string | number>>;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function Table({
  columns,
  rows,
  compact = false,
  className,
}: TableProps): React.ReactElement {
  const cellPadding = compact ? "px-2 py-1" : "px-3 py-2";

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full border-collapse border border-slate-200 dark:border-slate-700 text-sm">
        <thead>
          <tr className="bg-slate-100 dark:bg-slate-800">
            {columns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  "border border-slate-200 dark:border-slate-700",
                  "text-left font-medium text-slate-700 dark:text-slate-300",
                  cellPadding
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className="hover:bg-slate-50 dark:hover:bg-slate-900"
            >
              {columns.map((column) => (
                <td
                  key={`${rowIndex}-${column.key}`}
                  className={cn(
                    "border border-slate-200 dark:border-slate-700",
                    "text-slate-900 dark:text-slate-100",
                    cellPadding
                  )}
                >
                  {row[column.key] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
