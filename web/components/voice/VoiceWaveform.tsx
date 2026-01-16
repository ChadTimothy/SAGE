"use client";

/**
 * VoiceWaveform - Visual audio level indicator
 *
 * Updated for #87 - Accessibility for Voice/UI Parity
 */

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { useReducedMotion } from "@/hooks/useAccessibility";

export interface VoiceWaveformProps {
  audioLevel: number;
  isActive: boolean;
  className?: string;
  barCount?: number;
}

export function VoiceWaveform({
  audioLevel,
  isActive,
  className,
  barCount = 5,
}: VoiceWaveformProps): JSX.Element {
  const barsRef = useRef<HTMLDivElement[]>([]);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (!isActive || reducedMotion) return;

    barsRef.current.forEach((bar, index) => {
      if (!bar) return;

      // Create variation based on bar position and audio level
      const baseHeight = 0.3;
      const variation = Math.sin((index / barCount) * Math.PI) * 0.4;
      const randomness = Math.random() * 0.2;
      const height = baseHeight + (audioLevel * (variation + randomness + 0.3));

      bar.style.transform = `scaleY(${Math.min(height, 1)})`;
    });
  }, [audioLevel, isActive, barCount, reducedMotion]);

  // For screen readers: describe audio level
  const audioPercent = Math.round(audioLevel * 100);
  const audioDescription = isActive
    ? `Audio level: ${audioPercent}%`
    : "Audio visualization inactive";

  return (
    <div
      role="img"
      aria-label={audioDescription}
      aria-live="off"
      className={cn(
        "flex items-center justify-center gap-0.5 h-6",
        className
      )}
    >
      {Array.from({ length: barCount }).map((_, index) => (
        <div
          key={index}
          ref={(el) => {
            if (el) barsRef.current[index] = el;
          }}
          aria-hidden="true"
          className={cn(
            "w-1 h-full rounded-full",
            reducedMotion ? "" : "transition-transform duration-75",
            isActive ? "bg-red-500" : "bg-slate-300 dark:bg-slate-600"
          )}
          style={{
            transform: isActive && !reducedMotion ? undefined : "scaleY(0.3)",
          }}
        />
      ))}
    </div>
  );
}
