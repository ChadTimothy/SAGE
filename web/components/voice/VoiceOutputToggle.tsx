"use client";

import { Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/utils";

export interface VoiceOutputToggleProps {
  enabled: boolean;
  onToggle: () => void;
  disabled?: boolean;
  className?: string;
}

export function VoiceOutputToggle({
  enabled,
  onToggle,
  disabled = false,
  className,
}: VoiceOutputToggleProps): JSX.Element {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
        enabled
          ? "bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-400"
          : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
        "hover:bg-opacity-80",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      aria-label={enabled ? "Disable voice output" : "Enable voice output"}
      title={enabled ? "Voice output on" : "Voice output off"}
    >
      {enabled ? (
        <Volume2 className="h-4 w-4" />
      ) : (
        <VolumeX className="h-4 w-4" />
      )}
      <span className="hidden sm:inline">
        {enabled ? "Voice On" : "Voice Off"}
      </span>
    </button>
  );
}
