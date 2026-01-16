"use client";

/**
 * VoiceOutputToggle - Toggle for voice input/output
 *
 * Updated for #85 - Voice Error Recovery & Graceful Degradation
 * Updated for #87 - Accessibility for Voice/UI Parity
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

  // Accessible state description
  const stateDescription = hasError
    ? `Voice unavailable. ${errorMessage || "Click to retry."}`
    : enabled
    ? "Voice output enabled. Click to disable."
    : "Voice output disabled. Click to enable.";

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-offset-2",
        hasError
          ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 focus:ring-amber-500"
          : enabled
          ? "bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-400 focus:ring-sage-500"
          : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 focus:ring-slate-500",
        "hover:bg-opacity-80",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      aria-label={stateDescription}
      aria-pressed={enabled}
      aria-describedby={hasError ? "voice-error-desc" : undefined}
      title={
        hasError
          ? errorMessage || "Voice unavailable"
          : enabled
          ? "Voice output on"
          : "Voice output off"
      }
    >
      {hasError ? (
        <AlertTriangle className="h-4 w-4" aria-hidden="true" />
      ) : enabled ? (
        <Volume2 className="h-4 w-4" aria-hidden="true" />
      ) : (
        <VolumeX className="h-4 w-4" aria-hidden="true" />
      )}
      <span className="hidden sm:inline" aria-hidden="true">
        {hasError ? "Voice Error" : enabled ? "Voice On" : "Voice Off"}
      </span>
      {/* Screen reader only description for error state */}
      {hasError && (
        <span id="voice-error-desc" className="sr-only">
          {errorMessage || "Voice service error. Click to retry."}
        </span>
      )}
    </button>
  );
}
