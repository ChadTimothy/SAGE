"use client";

import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, AlertCircle, RotateCcw, ArrowRight, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PracticeScenario } from "./PracticeModeContainer";

export interface PracticeFeedbackData {
  scenario: PracticeScenario;
  positives: string[];
  improvements: string[];
  summary: string;
}

export interface PracticeFeedbackProps {
  isOpen: boolean;
  feedback: PracticeFeedbackData | null;
  onClose: () => void;
  onPracticeAgain: () => void;
  onBackToLearning: () => void;
}

export function PracticeFeedback({
  isOpen,
  feedback,
  onClose,
  onPracticeAgain,
  onBackToLearning,
}: PracticeFeedbackProps): JSX.Element | null {
  if (!isOpen || !feedback) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-lg mx-4 bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-amber-50 to-green-50 dark:from-amber-900/20 dark:to-green-900/20">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Practice Complete
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {feedback.scenario.title}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/50 dark:hover:bg-slate-800/50 transition-colors"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* What Worked */}
            {feedback.positives.length > 0 && (
              <div>
                <h3 className="flex items-center gap-2 text-sm font-semibold text-green-700 dark:text-green-400 mb-3">
                  <CheckCircle className="w-4 h-4" />
                  What worked
                </h3>
                <ul className="space-y-2">
                  {feedback.positives.map((item, index) => (
                    <motion.li
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300"
                    >
                      <span className="text-green-500 mt-0.5">✓</span>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </div>
            )}

            {/* To Improve */}
            {feedback.improvements.length > 0 && (
              <div>
                <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-400 mb-3">
                  <AlertCircle className="w-4 h-4" />
                  To improve
                </h3>
                <ul className="space-y-2">
                  {feedback.improvements.map((item, index) => (
                    <motion.li
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: (feedback.positives.length + index) * 0.1 }}
                      className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300"
                    >
                      <span className="text-amber-500 mt-0.5">→</span>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </div>
            )}

            {/* Summary */}
            <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {feedback.summary}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
            <button
              onClick={onPracticeAgain}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg",
                "border-2 border-amber-400 dark:border-amber-500",
                "text-amber-600 dark:text-amber-400 font-medium",
                "hover:bg-amber-50 dark:hover:bg-amber-900/20",
                "transition-colors"
              )}
            >
              <RotateCcw className="w-4 h-4" />
              Practice Again
            </button>
            <button
              onClick={onBackToLearning}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg",
                "bg-sage-600 text-white font-medium",
                "hover:bg-sage-700",
                "transition-colors"
              )}
            >
              Back to Learning
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
