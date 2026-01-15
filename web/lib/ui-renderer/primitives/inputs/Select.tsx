"use client";

/**
 * Select Primitive - Dropdown selection
 */

import { useId } from "react";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends PrimitiveProps {
  /** Field name (key in formData) */
  name: string;
  /** Select label */
  label: string;
  /** Available options */
  options: SelectOption[];
  /** Placeholder text */
  placeholder?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function Select({
  name,
  label,
  options,
  placeholder = "Select an option...",
  required = false,
  className,
  formData,
  setFormData,
}: SelectProps): React.ReactElement {
  const id = useId();
  const value = (formData[name] as string) || "";

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFormData((prev) => ({ ...prev, [name]: e.target.value }));
  };

  return (
    <div className={cn("space-y-1.5", className)}>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700 dark:text-slate-300"
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <select
        id={id}
        name={name}
        value={value}
        onChange={handleChange}
        required={required}
        className={cn(
          "w-full px-3 py-2 text-sm",
          "border border-slate-300 dark:border-slate-600 rounded-md",
          "bg-white dark:bg-slate-800",
          "text-slate-900 dark:text-slate-100",
          "focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          !value && "text-slate-400 dark:text-slate-500"
        )}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
