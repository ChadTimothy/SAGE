"use client";

/**
 * InlinePracticeSetup - Practice scenario selector rendered inline in the chat feed
 *
 * Replaces modal-based scenario selection for better conversation flow.
 * Appears as a SAGE message with scenario options.
 */

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Theater, MessageSquare, DollarSign, Users, Presentation, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { Scenario } from "@/types";
import type { PracticeScenario } from "@/components/practice/PracticeModeContainer";

export interface InlinePracticeSetupProps {
  onStart: (scenario: PracticeScenario) => void;
  onCancel: () => void;
  suggestedScenario?: string;
}

const SCENARIO_ICONS: Record<string, typeof DollarSign> = {
  "pricing-call": DollarSign,
  "pricing": DollarSign,
  "negotiation": Users,
  "presentation": Presentation,
  "interview": MessageSquare,
  "sales": DollarSign,
};

function getScenarioIcon(scenario: Scenario): typeof DollarSign {
  if (SCENARIO_ICONS[scenario.id]) return SCENARIO_ICONS[scenario.id];
  if (scenario.category && SCENARIO_ICONS[scenario.category]) {
    return SCENARIO_ICONS[scenario.category];
  }
  return MessageSquare;
}

function toFrontendScenario(scenario: Scenario): PracticeScenario {
  return {
    id: scenario.id,
    title: scenario.title,
    description: scenario.description || "Practice scenario",
    sageRole: scenario.sage_role,
    userRole: scenario.user_role,
  };
}

export function InlinePracticeSetup({
  onStart,
  onCancel,
  suggestedScenario,
}: InlinePracticeSetupProps): JSX.Element {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [customScenario, setCustomScenario] = useState("");
  const [customRole, setCustomRole] = useState("");
  const [showCustom, setShowCustom] = useState(false);

  useEffect(() => {
    const fetchScenarios = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.listScenarios(true);
        setScenarios(response.scenarios);
      } catch {
        try {
          const presetsResponse = await api.listPresetScenarios();
          setScenarios(presetsResponse.scenarios);
        } catch {
          setError("Failed to load scenarios");
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchScenarios();
  }, []);

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
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex w-full justify-start"
    >
      <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-md">
        <div className="flex items-center gap-2 mb-3">
          <Theater className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
            Practice Mode
          </span>
        </div>

        <div className="space-y-3">
          <p className="text-sm">
            Time to practice! Choose a scenario to rehearse, or create your own.
          </p>

          {suggestedScenario && (
            <div className="p-2 rounded-lg bg-sage-50 dark:bg-sage-900/30 border border-sage-200 dark:border-sage-800">
              <p className="text-xs text-sage-700 dark:text-sage-300">
                Suggested: <strong>{suggestedScenario}</strong>
              </p>
            </div>
          )}

          {!showCustom ? (
            <>
              {isLoading && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 text-amber-500 animate-spin" />
                  <span className="ml-2 text-sm text-slate-500">Loading scenarios...</span>
                </div>
              )}

              {error && (
                <div className="py-2 text-center text-sm text-red-500 dark:text-red-400">
                  {error}
                </div>
              )}

              {!isLoading && !error && scenarios.length > 0 && (
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {scenarios.slice(0, 6).map((scenario) => {
                    const Icon = getScenarioIcon(scenario);
                    return (
                      <button
                        key={scenario.id}
                        onClick={() => onStart(toFrontendScenario(scenario))}
                        className={cn(
                          "flex flex-col items-start p-2 rounded-lg border text-left text-xs",
                          "border-slate-200 dark:border-slate-600",
                          "hover:border-amber-400 dark:hover:border-amber-500",
                          "hover:bg-amber-50 dark:hover:bg-amber-900/20",
                          "transition-all"
                        )}
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <Icon className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                          {!scenario.is_preset && (
                            <span className="text-[9px] px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400">
                              Custom
                            </span>
                          )}
                        </div>
                        <span className="font-medium text-slate-900 dark:text-white line-clamp-1">
                          {scenario.title}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                          {scenario.description || `Play: ${scenario.user_role}`}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              {!isLoading && !error && scenarios.length === 0 && (
                <div className="py-4 text-center text-sm text-slate-500">
                  No scenarios available. Create a custom one below.
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => setShowCustom(true)}
                  className="flex-1 py-1.5 text-xs text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                >
                  Create custom scenario
                </button>
                <button
                  onClick={onCancel}
                  className="px-3 py-1.5 text-xs text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                  What do you want to practice?
                </label>
                <input
                  type="text"
                  value={customScenario}
                  onChange={(e) => setCustomScenario(e.target.value)}
                  placeholder="e.g., Asking for a raise"
                  className={cn(
                    "w-full px-3 py-2 rounded-lg text-sm",
                    "bg-white dark:bg-slate-700",
                    "text-slate-900 dark:text-white",
                    "placeholder:text-slate-400",
                    "border border-slate-200 dark:border-slate-600",
                    "focus:outline-none focus:ring-2 focus:ring-amber-500"
                  )}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                  Who should SAGE play? (optional)
                </label>
                <input
                  type="text"
                  value={customRole}
                  onChange={(e) => setCustomRole(e.target.value)}
                  placeholder="e.g., Your manager"
                  className={cn(
                    "w-full px-3 py-2 rounded-lg text-sm",
                    "bg-white dark:bg-slate-700",
                    "text-slate-900 dark:text-white",
                    "placeholder:text-slate-400",
                    "border border-slate-200 dark:border-slate-600",
                    "focus:outline-none focus:ring-2 focus:ring-amber-500"
                  )}
                />
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setShowCustom(false)}
                  className="flex-1 py-1.5 text-xs rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={handleCustomStart}
                  disabled={!customScenario.trim()}
                  className={cn(
                    "flex-1 py-1.5 text-xs rounded-lg font-medium transition-colors",
                    customScenario.trim()
                      ? "bg-amber-500 text-white hover:bg-amber-600"
                      : "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                  )}
                >
                  Start Practice
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
