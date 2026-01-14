"use client";

import { motion } from "framer-motion";
import { MessageSquare, Sparkles } from "lucide-react";

export interface EmptyStateProps {
  onSuggestionClick?: (suggestion: string) => void;
}

const suggestions = [
  "I want to learn how to negotiate better",
  "Help me understand machine learning basics",
  "I need to improve my public speaking",
  "Teach me about personal finance",
];

export function EmptyState({ onSuggestionClick }: EmptyStateProps): React.ReactElement {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center h-full p-8 text-center"
    >
      <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900 flex items-center justify-center mb-6">
        <MessageSquare className="w-8 h-8 text-sage-600 dark:text-sage-400" />
      </div>

      <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
        What do you want to learn?
      </h2>
      <p className="text-slate-600 dark:text-slate-400 mb-8 max-w-md">
        Tell me what you want to be able to DO, and I&apos;ll help you get there
        through conversation.
      </p>

      {/* Suggestions */}
      <div className="space-y-2 w-full max-w-md">
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-3">
          <Sparkles className="w-4 h-4" />
          <span>Try one of these:</span>
        </div>
        {suggestions.map((suggestion, index) => (
          <motion.button
            key={suggestion}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            onClick={() => onSuggestionClick?.(suggestion)}
            className="w-full text-left px-4 py-3 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors text-slate-700 dark:text-slate-300"
          >
            {suggestion}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
