"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Zap, Target, Waves, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SessionContext } from "@/types";

export interface CheckInModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (context: SessionContext) => void;
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

export function CheckInModal({
  isOpen,
  onClose,
  onComplete,
}: CheckInModalProps): JSX.Element {
  const [timeAvailable, setTimeAvailable] = useState<TimeOption>("focused");
  const [energyLevel, setEnergyLevel] = useState(50);
  const [mindset, setMindset] = useState("");

  const handleSubmit = () => {
    onComplete({ timeAvailable, energyLevel, mindset });
  };

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
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Energy level
                  </label>
                  <div className="flex items-center gap-3">
                    <span className="text-lg">😴</span>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={energyLevel}
                      onChange={(e) => setEnergyLevel(parseInt(e.target.value))}
                      className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-sage-500"
                    />
                    <span className="text-lg">🔥</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Anything on your mind?
                  </label>
                  <textarea
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
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
