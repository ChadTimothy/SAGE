"use client";

import { cn } from "@/lib/utils";
import type { GrokVoice } from "@/hooks/useGrokVoice";

export interface VoiceSelectorProps {
  value: GrokVoice;
  onChange: (voice: GrokVoice) => void;
  disabled?: boolean;
  className?: string;
}

const VOICES: { id: GrokVoice; name: string; description: string }[] = [
  { id: "ara", name: "Ara", description: "Female, warm" },
  { id: "rex", name: "Rex", description: "Male, confident" },
  { id: "sal", name: "Sal", description: "Neutral" },
  { id: "eve", name: "Eve", description: "Female, calm" },
  { id: "leo", name: "Leo", description: "Male, friendly" },
];

export function VoiceSelector({
  value,
  onChange,
  disabled = false,
  className,
}: VoiceSelectorProps): JSX.Element {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as GrokVoice)}
      disabled={disabled}
      className={cn(
        "px-3 py-1.5 rounded-lg text-sm",
        "bg-slate-100 dark:bg-slate-800",
        "text-slate-700 dark:text-slate-300",
        "border border-slate-200 dark:border-slate-700",
        "focus:outline-none focus:ring-2 focus:ring-sage-500",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
      aria-label="Select voice"
    >
      {VOICES.map((voice) => (
        <option key={voice.id} value={voice.id}>
          {voice.name} ({voice.description})
        </option>
      ))}
    </select>
  );
}
