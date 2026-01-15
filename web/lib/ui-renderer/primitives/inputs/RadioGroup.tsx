"use client";

/**
 * RadioGroup and Radio Primitives - Single selection from options
 */

import { createContext, useContext, useId } from "react";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

// Context for sharing radio group state
interface RadioContextValue {
  name: string;
  value: string;
  onChange: (value: string) => void;
}

const RadioContext = createContext<RadioContextValue | null>(null);

interface RadioGroupProps extends PrimitiveProps {
  /** Field name (key in formData) */
  name: string;
  /** Optional group label */
  label?: string;
  /** Additional CSS classes */
  className?: string;
}

export function RadioGroup({
  name,
  label,
  className,
  formData,
  setFormData,
  children,
}: RadioGroupProps): React.ReactElement {
  const value = (formData[name] as string) || "";

  const handleChange = (newValue: string) => {
    setFormData((prev) => ({ ...prev, [name]: newValue }));
  };

  return (
    <RadioContext.Provider value={{ name, value, onChange: handleChange }}>
      <fieldset className={cn("space-y-2", className)}>
        {label && (
          <legend className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            {label}
          </legend>
        )}
        <div className="space-y-2">{children}</div>
      </fieldset>
    </RadioContext.Provider>
  );
}

interface RadioProps extends Omit<PrimitiveProps, "formData" | "setFormData"> {
  /** Radio value */
  value: string;
  /** Radio label */
  label: string;
  /** Optional description */
  description?: string;
  /** Additional CSS classes */
  className?: string;
}

export function Radio({
  value,
  label,
  description,
  className,
}: RadioProps): React.ReactElement {
  const id = useId();
  const context = useContext(RadioContext);

  if (!context) {
    console.warn("Radio must be used within a RadioGroup");
    return <></>;
  }

  const { name, value: selectedValue, onChange } = context;
  const isSelected = selectedValue === value;

  return (
    <label
      htmlFor={id}
      className={cn(
        "flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors",
        "border",
        isSelected
          ? "border-sage-500 bg-sage-50 dark:bg-sage-950"
          : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600",
        className
      )}
    >
      <input
        id={id}
        type="radio"
        name={name}
        value={value}
        checked={isSelected}
        onChange={() => onChange(value)}
        className={cn(
          "mt-0.5 h-4 w-4",
          "border-slate-300 dark:border-slate-600",
          "text-sage-600 dark:text-sage-500",
          "focus:ring-sage-500"
        )}
      />
      <div className="flex-1">
        <span className="block text-sm font-medium text-slate-900 dark:text-slate-100">
          {label}
        </span>
        {description && (
          <span className="block text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {description}
          </span>
        )}
      </div>
    </label>
  );
}
