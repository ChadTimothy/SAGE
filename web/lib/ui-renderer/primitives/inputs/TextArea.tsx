"use client";

/**
 * TextArea Primitive - Multi-line text input
 */

import { useId } from "react";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface TextAreaProps extends PrimitiveProps {
  /** Field name (key in formData) */
  name: string;
  /** Label text */
  label: string;
  /** Placeholder text */
  placeholder?: string;
  /** Number of visible rows */
  rows?: number;
  /** Whether the field is required */
  required?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function TextArea({
  name,
  label,
  placeholder,
  rows = 3,
  required = false,
  className,
  formData,
  setFormData,
}: TextAreaProps): React.ReactElement {
  const id = useId();
  const value = (formData[name] as string) || "";

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
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
      <textarea
        id={id}
        name={name}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        rows={rows}
        required={required}
        className={cn(
          "w-full px-3 py-2 text-sm",
          "border border-slate-300 dark:border-slate-600 rounded-md",
          "bg-white dark:bg-slate-800",
          "text-slate-900 dark:text-slate-100",
          "placeholder:text-slate-400 dark:placeholder:text-slate-500",
          "focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "resize-none"
        )}
      />
    </div>
  );
}
