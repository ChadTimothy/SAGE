"use client";

/**
 * TextArea Primitive - Multi-line text input
 *
 * Updated for #87 - Accessibility for Voice/UI Parity
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
  /** Helper text below input */
  description?: string;
  /** Error message */
  error?: string;
  /** Additional CSS classes */
  className?: string;
}

export function TextArea({
  name,
  label,
  placeholder,
  rows = 3,
  required = false,
  description,
  error,
  className,
  formData,
  setFormData,
}: TextAreaProps): React.ReactElement {
  const id = useId();
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;
  const value = (formData[name] as string) || "";

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFormData((prev) => ({ ...prev, [name]: e.target.value }));
  };

  // Build aria-describedby value
  const describedBy = [
    description ? descriptionId : null,
    error ? errorId : null,
  ]
    .filter(Boolean)
    .join(" ") || undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700 dark:text-slate-300"
      >
        {label}
        {required && (
          <span className="text-red-500 ml-1" aria-hidden="true">
            *
          </span>
        )}
        {required && <span className="sr-only">(required)</span>}
      </label>
      <textarea
        id={id}
        name={name}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        rows={rows}
        required={required}
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
        className={cn(
          "w-full px-3 py-2 text-sm",
          "border rounded-md",
          error
            ? "border-red-500 dark:border-red-400"
            : "border-slate-300 dark:border-slate-600",
          "bg-white dark:bg-slate-800",
          "text-slate-900 dark:text-slate-100",
          "placeholder:text-slate-400 dark:placeholder:text-slate-500",
          "focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "resize-none"
        )}
      />
      {description && !error && (
        <p
          id={descriptionId}
          className="text-xs text-slate-500 dark:text-slate-400"
        >
          {description}
        </p>
      )}
      {error && (
        <p
          id={errorId}
          role="alert"
          className="text-xs text-red-600 dark:text-red-400"
        >
          {error}
        </p>
      )}
    </div>
  );
}
