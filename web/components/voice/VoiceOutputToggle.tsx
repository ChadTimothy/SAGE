"use client";

/**
 * VoiceOutputToggle - Toggle for voice input/output
 *
 * Updated for #85 - Voice Error Recovery & Graceful Degradation
 */

import { Volume2, VolumeX, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface VoiceOutputToggleProps {
  enabled: boolean;
  onToggle: () => void;
  disabled?: boolean;
  error?: boolean;
  errorMessage?: string;
  className?: string;
}

export function VoiceOutputToggle({
  enabled,
  onToggle,
  disabled = false,
  error = false,
  errorMessage,
  className,
}: VoiceOutputToggleProps): JSX.Element {
  const hasError = error && !enabled;

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
        hasError
          ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
          : enabled
          ? "bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-400"
          : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
        "hover:bg-opacity-80",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      aria-label={
        hasError
          ? "Voice unavailable - click to retry"
          : enabled
          ? "Disable voice output"
          : "Enable voice output"
      }
      title={
        hasError
          ? errorMessage || "Voice unavailable"
          : enabled
          ? "Voice output on"
          : "Voice output off"
      }
    >
      {hasError ? (
        <AlertTriangle className="h-4 w-4" />
      ) : enabled ? (
        <Volume2 className="h-4 w-4" />
      ) : (
        <VolumeX className="h-4 w-4" />
      )}
      <span className="hidden sm:inline">
        {hasError ? "Voice Error" : enabled ? "Voice On" : "Voice Off"}
      </span>
    </button>
  );
}
