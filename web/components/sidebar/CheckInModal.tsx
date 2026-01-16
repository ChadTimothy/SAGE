"use client";

/**
 * CheckInModal - Session check-in for gathering learner context
 *
 * Updated for #59 - Voice mode and dual input support
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Zap, Target, Waves, ArrowRight, Mic, MousePointer, Combine } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SessionContext } from "@/types";

export type InputMode = "form" | "voice" | "both";

export interface CheckInModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (context: SessionContext) => void;
  /** Prefill data from voice input */
  prefillData?: Partial<SessionContext>;
  /** Callback when input mode changes */
  onInputModeChange?: (mode: InputMode) => void;
  /** Whether voice is currently available */
  voiceAvailable?: boolean;
}

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

interface InputModeOption {
  value: InputMode;
  label: string;
  description: string;
  icon: JSX.Element;
}

const inputModeOptions: InputModeOption[] = [
  {
    value: "form",
    label: "Form",
    description: "Fill in the form below",
    icon: <MousePointer className="h-4 w-4" />,
  },
  {
    value: "voice",
    label: "Voice",
    description: "Tell me conversationally",
    icon: <Mic className="h-4 w-4" />,
  },
  {
    value: "both",
    label: "Both",
    description: "Use voice and form together",
    icon: <Combine className="h-4 w-4" />,
  },
];

export function CheckInModal({
  isOpen,
  onClose,
  onComplete,
  prefillData,
  onInputModeChange,
  voiceAvailable = true,
}: CheckInModalProps): JSX.Element {
  const [inputMode, setInputMode] = useState<InputMode>("form");
  const [timeAvailable, setTimeAvailable] = useState<TimeOption>("focused");
  const [energyLevel, setEnergyLevel] = useState(50);
  const [mindset, setMindset] = useState("");

  // Sync form state with prefill data from voice
  useEffect(() => {
    if (prefillData) {
      if (prefillData.timeAvailable) {
        setTimeAvailable(prefillData.timeAvailable);
      }
      if (prefillData.energyLevel !== undefined) {
        setEnergyLevel(prefillData.energyLevel);
      }
      if (prefillData.mindset) {
        setMindset(prefillData.mindset);
      }
    }
  }, [prefillData]);

  const handleInputModeChange = (mode: InputMode) => {
    setInputMode(mode);
    onInputModeChange?.(mode);
  };

  const handleSubmit = () => {
    onComplete({ timeAvailable, energyLevel, mindset });
  };

  const showForm = inputMode === "form" || inputMode === "both";
  const showVoiceHint = inputMode === "voice" || inputMode === "both";

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.3 }}
            className="fixed inset-x-4 top-[10%] md:inset-x-auto md:left-1/2 md:-translate-x-1/2 md:w-full md:max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-xl z-50 overflow-hidden"
          >
            <div className="relative p-6">
              <button
                onClick={onClose}
                className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>

              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
                    How are you showing up today?
                  </h2>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Help me tailor this session to you
                  </p>
                </div>

                {/* Input Mode Selector */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    How would you like to check in?
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {inputModeOptions.map((option) => {
                      const isDisabled = option.value !== "form" && !voiceAvailable;
                      return (
                        <button
                          key={option.value}
                          onClick={() => handleInputModeChange(option.value)}
                          disabled={isDisabled}
                          className={cn(
                            "flex flex-col items-center gap-1 p-2 rounded-lg border transition-all text-sm",
                            inputMode === option.value
                              ? "border-sage-500 bg-sage-50 dark:bg-sage-900/20 text-sage-700 dark:text-sage-300"
                              : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600",
                            isDisabled && "opacity-50 cursor-not-allowed"
                          )}
                          aria-pressed={inputMode === option.value}
                        >
                          {option.icon}
                          <span className="font-medium">{option.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Voice hint when in voice/both mode */}
                {showVoiceHint && (
                  <div className="p-3 bg-sage-50 dark:bg-sage-900/20 rounded-lg border border-sage-200 dark:border-sage-800">
                    <p className="text-sm text-sage-700 dark:text-sage-300">
                      <Mic className="h-4 w-4 inline mr-2" />
                      Try saying: &quot;I have about 30 minutes, feeling pretty tired, have a presentation tomorrow&quot;
                    </p>
                  </div>
                )}

                {/* Form fields - shown in form/both mode */}
                {showForm && (
                  <>
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                        Time available
                      </label>
                      <div className="grid grid-cols-3 gap-3">
                        {timeOptions.map((option) => (
                          <button
                            key={option.value}
                            onClick={() => setTimeAvailable(option.value)}
                            className={cn(
                              "flex flex-col items-center gap-1 p-3 rounded-xl border-2 transition-all",
                              timeAvailable === option.value
                                ? "border-sage-500 bg-sage-50 dark:bg-sage-900/20 text-sage-700 dark:text-sage-300"
                                : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
                            )}
                            aria-pressed={timeAvailable === option.value}
                          >
                            {option.icon}
                            <span className="text-sm font-medium">{option.label}</span>
                            <span className="text-xs text-slate-500 dark:text-slate-400">
                              {option.duration}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label
                        htmlFor="energy-slider"
                        className="block text-sm font-medium text-slate-700 dark:text-slate-300"
                      >
                        Energy level
                      </label>
                      <div className="flex items-center gap-3">
                        <span className="text-lg" aria-hidden="true">😴</span>
                        <input
                          id="energy-slider"
                          type="range"
                          min="0"
                          max="100"
                          value={energyLevel}
                          onChange={(e) => setEnergyLevel(parseInt(e.target.value))}
                          className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-sage-500"
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-valuenow={energyLevel}
                        />
                        <span className="text-lg" aria-hidden="true">🔥</span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label
                        htmlFor="mindset-input"
                        className="block text-sm font-medium text-slate-700 dark:text-slate-300"
                      >
                        Anything on your mind?
                      </label>
                      <textarea
                        id="mindset-input"
                        value={mindset}
                        onChange={(e) => setMindset(e.target.value)}
                        placeholder="e.g., Have a pricing call tomorrow, feeling nervous"
                        rows={2}
                        className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent resize-none"
                      />
                    </div>

                    <button
                      onClick={handleSubmit}
                      className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-sage-600 hover:bg-sage-700 text-white font-medium rounded-xl transition-colors"
                    >
                      Let&apos;s begin
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </>
                )}

                {/* Voice-only mode message */}
                {inputMode === "voice" && (
                  <div className="text-center py-4">
                    <p className="text-slate-600 dark:text-slate-400">
                      Just start talking! I&apos;ll gather your check-in through our conversation.
                    </p>
                    <button
                      onClick={onClose}
                      className="mt-4 px-6 py-2 text-sage-600 dark:text-sage-400 hover:underline"
                    >
                      Close and start chatting
                    </button>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
