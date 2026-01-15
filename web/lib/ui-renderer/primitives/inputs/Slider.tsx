"use client";

/**
 * Slider Primitive - Numeric range input with emoji endpoints
 */

import { useId } from "react";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface SliderProps extends PrimitiveProps {
  /** Field name (key in formData) */
  name: string;
  /** Label text */
  label: string;
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step increment */
  step?: number;
  /** Left endpoint emoji */
  leftEmoji?: string;
  /** Right endpoint emoji */
  rightEmoji?: string;
  /** Whether to show the current value */
  showValue?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function Slider({
  name,
  label,
  min = 0,
  max = 100,
  step = 1,
  leftEmoji,
  rightEmoji,
  showValue = true,
  className,
  formData,
  setFormData,
}: SliderProps): React.ReactElement {
  const id = useId();
  const value = (formData[name] as number) ?? Math.round((min + max) / 2);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [name]: Number(e.target.value) }));
  };

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex justify-between items-center">
        <label
          htmlFor={id}
          className="text-sm font-medium text-slate-700 dark:text-slate-300"
        >
          {label}
        </label>
        {showValue && (
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {value}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {leftEmoji && (
          <span className="text-lg" aria-hidden="true">
            {leftEmoji}
          </span>
        )}
        <input
          id={id}
          type="range"
          name={name}
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleChange}
          className={cn(
            "w-full h-2 rounded-full appearance-none cursor-pointer",
            "bg-slate-200 dark:bg-slate-700",
            "[&::-webkit-slider-thumb]:appearance-none",
            "[&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4",
            "[&::-webkit-slider-thumb]:rounded-full",
            "[&::-webkit-slider-thumb]:bg-sage-600 dark:[&::-webkit-slider-thumb]:bg-sage-500",
            "[&::-webkit-slider-thumb]:cursor-pointer",
            "[&::-webkit-slider-thumb]:transition-transform",
            "[&::-webkit-slider-thumb]:hover:scale-110",
            "[&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4",
            "[&::-moz-range-thumb]:rounded-full",
            "[&::-moz-range-thumb]:bg-sage-600 dark:[&::-moz-range-thumb]:bg-sage-500",
            "[&::-moz-range-thumb]:border-none",
            "[&::-moz-range-thumb]:cursor-pointer"
          )}
        />
        {rightEmoji && (
          <span className="text-lg" aria-hidden="true">
            {rightEmoji}
          </span>
        )}
      </div>
    </div>
  );
}
