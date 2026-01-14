"use client";

import { motion } from "framer-motion";
import { cn, formatTime, formatDialogueMode } from "@/lib/utils";
import { MarkdownContent } from "./MarkdownContent";
import type { DialogueMode } from "@/types";

export interface MessageBubbleProps {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  mode?: DialogueMode;
}

const ANIMATION_CONFIG = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.2 },
};

export function MessageBubble({
  role,
  content,
  timestamp,
  isStreaming = false,
  mode,
}: MessageBubbleProps): JSX.Element {
  const isUser = role === "user";
  const formattedTime = formatTime(timestamp);

  if (role === "system") {
    return (
      <motion.div {...ANIMATION_CONFIG} className="flex justify-center w-full">
        <div className="px-4 py-2 text-sm text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 rounded-full">
          {content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      {...ANIMATION_CONFIG}
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-sage-600 text-white rounded-br-md"
            : "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-md"
        )}
      >
        {!isUser && (
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
        )}

        <div className="break-words">
          {isUser ? (
            <div className="whitespace-pre-wrap">{content}</div>
          ) : (
            <MarkdownContent content={content} />
          )}
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-sage-600 dark:bg-sage-400 animate-pulse" />
          )}
        </div>

        <div
          className={cn(
            "text-xs mt-2",
            isUser ? "text-sage-200" : "text-slate-500 dark:text-slate-400"
          )}
        >
          {formattedTime}
        </div>
      </div>
    </motion.div>
  );
}
