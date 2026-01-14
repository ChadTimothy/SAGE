"use client";

import { motion } from "framer-motion";
import { formatDialogueMode } from "@/lib/utils";
import type { DialogueMode } from "@/types";

export interface StreamingIndicatorProps {
  mode?: DialogueMode;
}

export function StreamingIndicator({ mode }: StreamingIndicatorProps): JSX.Element {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex justify-start w-full"
    >
      <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-bl-md px-4 py-3 max-w-[80%]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-sage-600 dark:text-sage-400">
            SAGE
          </span>
          {mode && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {formatDialogueMode(mode)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-600 dark:text-slate-400">
            Thinking
          </span>
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="w-2 h-2 bg-sage-500 rounded-full"
                animate={{
                  scale: [1, 1.2, 1],
                  opacity: [0.5, 1, 0.5],
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
