"use client";

/**
 * VoiceErrorToast - Error toast for voice-related errors
 *
 * Part of #85 - Voice Error Recovery & Graceful Degradation
 */

import { AlertCircle, RefreshCw, Keyboard } from "lucide-react";
import { cn } from "@/lib/utils";

export type VoiceErrorType =
  | "mic_denied"
  | "mic_not_found"
  | "connection_error"
  | "api_error"
  | "timeout"
  | "browser_unsupported"
  | "unknown";

export interface VoiceError {
  type: VoiceErrorType;
  message: string;
  recoverable: boolean;
}

export interface VoiceErrorToastProps {
  error: VoiceError;
  onRetry?: () => void;
  onFallback?: () => void;
  onDismiss?: () => void;
  className?: string;
}

const ERROR_TITLES: Record<VoiceErrorType, string> = {
  mic_denied: "Microphone Access Denied",
  mic_not_found: "Microphone Not Found",
  connection_error: "Voice Connection Lost",
  api_error: "Voice Service Error",
  timeout: "No Speech Detected",
  browser_unsupported: "Voice Not Supported",
  unknown: "Voice Error",
};

const ERROR_HINTS: Record<VoiceErrorType, string> = {
  mic_denied: "Check your browser settings to enable microphone access.",
  mic_not_found: "Connect a microphone and try again.",
  connection_error: "Your connection may have dropped. Try reconnecting.",
  api_error: "The voice service is temporarily unavailable.",
  timeout: "Try speaking louder or closer to your microphone.",
  browser_unsupported: "Try using Chrome, Firefox, or Edge for voice features.",
  unknown: "Something went wrong with voice input.",
};

export function VoiceErrorToast({
  error,
  onRetry,
  onFallback,
  onDismiss,
  className,
}: VoiceErrorToastProps): JSX.Element {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col gap-2 p-4 rounded-lg border",
        "bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800",
        "shadow-lg max-w-sm",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-amber-800 dark:text-amber-200">
            {ERROR_TITLES[error.type]}
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
            {error.message || ERROR_HINTS[error.type]}
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-amber-600 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-200"
            aria-label="Dismiss"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="flex gap-2 mt-1">
        {error.recoverable && onRetry && (
          <button
            onClick={onRetry}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded",
              "bg-amber-600 text-white hover:bg-amber-700",
              "dark:bg-amber-500 dark:hover:bg-amber-600"
            )}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Try Again
          </button>
        )}
        {onFallback && (
          <button
            onClick={onFallback}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded",
              "bg-amber-100 text-amber-800 hover:bg-amber-200",
              "dark:bg-amber-800/30 dark:text-amber-200 dark:hover:bg-amber-800/50"
            )}
          >
            <Keyboard className="h-3.5 w-3.5" />
            Use Text Instead
          </button>
        )}
      </div>
    </div>
  );
}

export default VoiceErrorToast;
