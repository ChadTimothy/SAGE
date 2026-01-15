"use client";

/**
 * Checkbox Primitive - Boolean toggle
 */

import { useId } from "react";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface CheckboxProps extends PrimitiveProps {
  /** Field name (key in formData) */
  name: string;
  /** Checkbox label */
  label: string;
  /** Optional description */
  description?: string;
  /** Additional CSS classes */
  className?: string;
}

export function Checkbox({
  name,
  label,
  description,
  className,
  formData,
  setFormData,
}: CheckboxProps): React.ReactElement {
  const id = useId();
  const checked = Boolean(formData[name]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [name]: e.target.checked }));
  };

  return (
    <div className={cn("flex items-start gap-3", className)}>
      <input
        id={id}
        type="checkbox"
        name={name}
        checked={checked}
        onChange={handleChange}
        className={cn(
          "mt-1 h-4 w-4 rounded",
          "border-slate-300 dark:border-slate-600",
          "text-sage-600 dark:text-sage-500",
          "focus:ring-sage-500",
          "cursor-pointer"
        )}
      />
      <label htmlFor={id} className="cursor-pointer">
        <span className="block text-sm font-medium text-slate-900 dark:text-slate-100">
          {label}
        </span>
        {description && (
          <span className="block text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {description}
          </span>
        )}
      </label>
    </div>
  );
}
