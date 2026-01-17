"use client";

/**
 * InlineCheckIn - Session check-in form rendered inline in the chat feed
 *
 * Replaces modal-based check-in for better conversation flow.
 * Appears as a SAGE message with an embedded form.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import { Zap, Target, Waves, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SessionContext } from "@/types";

type TimeOption = SessionContext["timeAvailable"];

interface TimeOptionConfig {
  value: TimeOption;
  label: string;
  duration: string;
  icon: JSX.Element;
}

const timeOptions: TimeOptionConfig[] = [
  { value: "quick", label: "Quick", duration: "15 min", icon: <Zap className="h-5 w-5" /> },
  { value: "focused", label: "Focused", duration: "45 min", icon: <Target className="h-5 w-5" /> },
  { value: "deep", label: "Deep", duration: "open-ended", icon: <Waves className="h-5 w-5" /> },
];

export interface InlineCheckInProps {
  onComplete: (context: SessionContext) => void;
  isLoading?: boolean;
}

export function InlineCheckIn({
  onComplete,
  isLoading = false,
}: InlineCheckInProps): JSX.Element {
  const [timeAvailable, setTimeAvailable] = useState<TimeOption>("focused");
  const [energyLevel, setEnergyLevel] = useState(50);
  const [mindset, setMindset] = useState("");

  const handleSubmit = () => {
    onComplete({ timeAvailable, energyLevel, mindset });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex w-full justify-start"
    >
      <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-md">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold text-sage-600 dark:text-sage-400">
            SAGE
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Check-in
          </span>
        </div>

        <div className="space-y-4">
          <p className="text-sm">
            How are you showing up today? This helps me tailor our session.
          </p>

          {/* Time Available */}
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Time available
            </label>
            <div className="grid grid-cols-3 gap-2">
              {timeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setTimeAvailable(option.value)}
                  disabled={isLoading}
                  className={cn(
                    "flex flex-col items-center gap-1 p-2 rounded-lg border transition-all text-xs",
                    timeAvailable === option.value
                      ? "border-sage-500 bg-sage-50 dark:bg-sage-900/30 text-sage-700 dark:text-sage-300"
                      : "border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500"
                  )}
                  aria-pressed={timeAvailable === option.value}
                >
                  {option.icon}
                  <span className="font-medium">{option.label}</span>
                  <span className="text-slate-500 dark:text-slate-400">
                    {option.duration}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Energy Level */}
          <div className="space-y-2">
            <label
              htmlFor="inline-energy-slider"
              className="block text-xs font-medium text-slate-600 dark:text-slate-400"
            >
              Energy level
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm" aria-hidden="true">😴</span>
              <input
                id="inline-energy-slider"
                type="range"
                min="0"
                max="100"
                value={energyLevel}
                onChange={(e) => setEnergyLevel(parseInt(e.target.value))}
                disabled={isLoading}
                className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-sage-500"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={energyLevel}
              />
              <span className="text-sm" aria-hidden="true">🔥</span>
            </div>
          </div>

          {/* Mindset */}
          <div className="space-y-2">
            <label
              htmlFor="inline-mindset-input"
              className="block text-xs font-medium text-slate-600 dark:text-slate-400"
            >
              Anything on your mind? (optional)
            </label>
            <textarea
              id="inline-mindset-input"
              value={mindset}
              onChange={(e) => setMindset(e.target.value)}
              placeholder="e.g., Have a meeting tomorrow, feeling nervous"
              rows={2}
              disabled={isLoading}
              className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent resize-none disabled:opacity-50"
            />
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className={cn(
              "w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
              isLoading
                ? "bg-sage-400 cursor-not-allowed"
                : "bg-sage-600 hover:bg-sage-700",
              "text-white"
            )}
          >
            {isLoading ? (
              <>
                <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Starting session...
              </>
            ) : (
              <>
                Let&apos;s begin
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
