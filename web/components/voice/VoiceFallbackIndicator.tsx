"use client";

/**
 * VoiceFallbackIndicator - Shows when voice is unavailable
 *
 * Part of #85 - Voice Error Recovery & Graceful Degradation
 */

import { MicOff, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export interface VoiceFallbackIndicatorProps {
  reason?: string;
  onRetry?: () => void;
  className?: string;
}

export function VoiceFallbackIndicator({
  reason = "Voice unavailable",
  onRetry,
  className,
}: VoiceFallbackIndicatorProps): JSX.Element {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400",
        className
      )}
    >
      <MicOff className="h-3 w-3" />
      <span>{reason}</span>
      {onRetry && (
        <>
          <span className="text-slate-400">•</span>
          <button
            onClick={onRetry}
            className="flex items-center gap-1 hover:text-amber-700 dark:hover:text-amber-300 underline underline-offset-2"
          >
            <RefreshCw className="h-3 w-3" />
            Try again
          </button>
        </>
      )}
    </div>
  );
}

export default VoiceFallbackIndicator;
