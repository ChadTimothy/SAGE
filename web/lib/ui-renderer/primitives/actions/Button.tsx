"use client";

/**
 * Button Primitive - Triggers actions
 */

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { scaleVariants } from "../../animations";
import type { PrimitiveProps } from "../../types";

interface ButtonProps extends PrimitiveProps {
  /** Action name sent to handler */
  action: string;
  /** Button label */
  label: string;
  /** Button variant */
  variant?: "primary" | "secondary" | "ghost" | "danger";
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Button type */
  type?: "button" | "submit";
  /** Additional CSS classes */
  className?: string;
}

const variantClasses: Record<string, string> = {
  primary: cn(
    "bg-sage-600 text-white shadow-sm",
    "hover:bg-sage-700",
    "focus:ring-sage-500"
  ),
  secondary: cn(
    "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm",
    "hover:bg-slate-200 dark:hover:bg-slate-700",
    "focus:ring-slate-500"
  ),
  ghost: cn(
    "text-slate-600 dark:text-slate-400",
    "hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100",
    "focus:ring-slate-500"
  ),
  danger: cn(
    "bg-red-600 text-white shadow-sm",
    "hover:bg-red-700",
    "focus:ring-red-500"
  ),
};

export function Button({
  action,
  label,
  variant = "primary",
  disabled = false,
  type = "button",
  className,
  onAction,
}: ButtonProps): React.ReactElement {
  const handleClick = () => {
    if (!disabled) {
      onAction({ name: action, data: {} });
    }
  };

  return (
    <motion.button
      type={type}
      onClick={handleClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center gap-2",
        "px-4 py-2 text-sm font-medium rounded-md",
        "transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-offset-2",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variantClasses[variant],
        className
      )}
      variants={scaleVariants}
      initial="initial"
      animate="animate"
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
    >
      {label}
    </motion.button>
  );
}
