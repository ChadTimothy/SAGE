"use client";

import { X, Target, BookOpen, Award, Circle, Check, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { KnowledgeNode, KnowledgeNodeStatus } from "@/types";

export interface NodeDetailPanelProps {
  node: KnowledgeNode | null;
  onClose: () => void;
}

function getStatusIcon(status: KnowledgeNodeStatus): JSX.Element {
  switch (status) {
    case "proven":
    case "achieved":
      return <Check className="h-4 w-4 text-green-500" />;
    case "in_progress":
    case "active":
      return <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />;
    case "identified":
    default:
      return <Circle className="h-4 w-4 text-slate-400" />;
  }
}

function getStatusLabel(status: KnowledgeNodeStatus): string {
  switch (status) {
    case "proven":
      return "Proven";
    case "achieved":
      return "Achieved";
    case "in_progress":
      return "In Progress";
    case "active":
      return "Active";
    case "identified":
    default:
      return "Identified";
  }
}

function getStatusColor(status: KnowledgeNodeStatus): string {
  switch (status) {
    case "proven":
    case "achieved":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    case "in_progress":
    case "active":
      return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
    case "identified":
    default:
      return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400";
  }
}

export function NodeDetailPanel({ node, onClose }: NodeDetailPanelProps): JSX.Element {
  return (
    <AnimatePresence>
      {node && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          transition={{ duration: 0.2 }}
          className="absolute top-4 right-4 w-80 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden"
        >
          <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2">
              {node.type === "outcome" ? (
                <Target className="h-5 w-5 text-indigo-500" />
              ) : (
                <BookOpen className="h-5 w-5 text-sage-500" />
              )}
              <span className="font-medium text-slate-900 dark:text-white">
                {node.type === "outcome" ? "Goal" : "Concept"}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
              <X className="h-4 w-4 text-slate-500" />
            </button>
          </div>

          <div className="p-4 space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                {node.label}
              </h3>
              {node.description && (
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  {node.description}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
                  getStatusColor(node.status)
                )}
              >
                {getStatusIcon(node.status)}
                {getStatusLabel(node.status)}
              </span>
            </div>

            {node.type === "concept" && node.proofCount !== undefined && node.proofCount > 0 && (
              <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                <Award className="h-4 w-4 text-green-500" />
                <span>
                  {node.proofCount} proof{node.proofCount !== 1 ? "s" : ""} earned
                </span>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
