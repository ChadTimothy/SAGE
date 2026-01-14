"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Theater, MessageSquare, DollarSign, Users, Presentation, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PracticeScenario } from "./PracticeModeContainer";

export interface PracticeScenarioSetupProps {
  isOpen: boolean;
  onClose: () => void;
  onStart: (scenario: PracticeScenario) => void;
  suggestedScenario?: string;
}

const PRESET_SCENARIOS: PracticeScenario[] = [
  {
    id: "pricing-call",
    title: "Pricing Call",
    description: "Practice handling price objections and negotiating your rates",
    sageRole: "Potential client asking for discounts",
    userRole: "Service provider",
  },
  {
    id: "negotiation",
    title: "Negotiation",
    description: "Practice negotiation tactics with a counterparty",
    sageRole: "Negotiation counterparty",
    userRole: "Negotiator",
  },
  {
    id: "presentation",
    title: "Presentation Q&A",
    description: "Practice answering tough questions from your audience",
    sageRole: "Audience member asking challenging questions",
    userRole: "Presenter",
  },
  {
    id: "interview",
    title: "Job Interview",
    description: "Practice common interview questions and scenarios",
    sageRole: "Interviewer",
    userRole: "Job candidate",
  },
];

const SCENARIO_ICONS: Record<string, typeof DollarSign> = {
  "pricing-call": DollarSign,
  negotiation: Users,
  presentation: Presentation,
  interview: MessageSquare,
};

export function PracticeScenarioSetup({
  isOpen,
  onClose,
  onStart,
  suggestedScenario,
}: PracticeScenarioSetupProps): JSX.Element | null {
  const [customScenario, setCustomScenario] = useState("");
  const [customRole, setCustomRole] = useState("");
  const [showCustom, setShowCustom] = useState(false);

  if (!isOpen) return null;

  const handleCustomStart = () => {
    if (!customScenario.trim()) return;

    const scenario: PracticeScenario = {
      id: `custom-${Date.now()}`,
      title: customScenario,
      description: "Custom practice scenario",
      sageRole: customRole || "The other party",
      userRole: "You",
    };
    onStart(scenario);
  };

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
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30">
                <Theater className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                  Start Practice
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Choose a scenario to rehearse
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {suggestedScenario && (
              <div className="mb-4 p-3 rounded-lg bg-sage-50 dark:bg-sage-900/20 border border-sage-200 dark:border-sage-800">
                <p className="text-sm text-sage-700 dark:text-sage-300">
                  Based on your conversation: <strong>{suggestedScenario}</strong>
                </p>
              </div>
            )}

            {!showCustom ? (
              <>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  {PRESET_SCENARIOS.map((scenario) => {
                    const Icon = SCENARIO_ICONS[scenario.id] || MessageSquare;
                    return (
                      <button
                        key={scenario.id}
                        onClick={() => onStart(scenario)}
                        className={cn(
                          "flex flex-col items-start p-4 rounded-xl border-2 text-left",
                          "border-slate-200 dark:border-slate-700",
                          "hover:border-amber-400 dark:hover:border-amber-500",
                          "hover:bg-amber-50 dark:hover:bg-amber-900/10",
                          "transition-all"
                        )}
                      >
                        <Icon className="w-5 h-5 text-amber-600 dark:text-amber-400 mb-2" />
                        <span className="font-medium text-slate-900 dark:text-white">
                          {scenario.title}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          {scenario.description}
                        </span>
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => setShowCustom(true)}
                  className="w-full py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  Or create a custom scenario...
                </button>
              </>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    What do you want to practice?
                  </label>
                  <input
                    type="text"
                    value={customScenario}
                    onChange={(e) => setCustomScenario(e.target.value)}
                    placeholder="e.g., Asking for a raise"
                    className={cn(
                      "w-full px-4 py-2 rounded-lg",
                      "bg-slate-100 dark:bg-slate-800",
                      "text-slate-900 dark:text-white",
                      "placeholder:text-slate-500",
                      "border border-slate-200 dark:border-slate-700",
                      "focus:outline-none focus:ring-2 focus:ring-amber-500"
                    )}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Who should SAGE play? (optional)
                  </label>
                  <input
                    type="text"
                    value={customRole}
                    onChange={(e) => setCustomRole(e.target.value)}
                    placeholder="e.g., Your manager"
                    className={cn(
                      "w-full px-4 py-2 rounded-lg",
                      "bg-slate-100 dark:bg-slate-800",
                      "text-slate-900 dark:text-white",
                      "placeholder:text-slate-500",
                      "border border-slate-200 dark:border-slate-700",
                      "focus:outline-none focus:ring-2 focus:ring-amber-500"
                    )}
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowCustom(false)}
                    className="flex-1 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleCustomStart}
                    disabled={!customScenario.trim()}
                    className={cn(
                      "flex-1 py-2 rounded-lg font-medium transition-colors",
                      customScenario.trim()
                        ? "bg-amber-500 text-white hover:bg-amber-600"
                        : "bg-slate-200 text-slate-400 cursor-not-allowed"
                    )}
                  >
                    Start Practice
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
