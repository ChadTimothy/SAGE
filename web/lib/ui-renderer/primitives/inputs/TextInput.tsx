"use client";

/**
 * TextInput Primitive - Single-line text input
 *
 * Updated for #87 - Accessibility for Voice/UI Parity
 */

import { useId } from "react";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface TextInputProps extends PrimitiveProps {
  /** Field name (key in formData) */
  name: string;
  /** Label text */
  label: string;
  /** Placeholder text */
  placeholder?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Input type */
  type?: "text" | "email" | "number" | "tel" | "url";
  /** Helper text below input */
  description?: string;
  /** Error message */
  error?: string;
  /** Additional CSS classes */
  className?: string;
}

export function TextInput({
  name,
  label,
  placeholder,
  required = false,
  type = "text",
  description,
  error,
  className,
  formData,
  setFormData,
}: TextInputProps): React.ReactElement {
  const id = useId();
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;
  const value = (formData[name] as string) || "";

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [name]: e.target.value }));
  };

  const describedByParts = [
    description && descriptionId,
    error && errorId,
  ].filter(Boolean);
  const describedBy = describedByParts.length > 0 ? describedByParts.join(" ") : undefined;

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
      <input
        id={id}
        type={type}
        name={name}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
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
          "disabled:opacity-50 disabled:cursor-not-allowed"
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
