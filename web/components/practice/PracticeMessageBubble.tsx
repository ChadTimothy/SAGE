"use client";

import { motion } from "framer-motion";
import { cn, formatTime } from "@/lib/utils";
import { MarkdownContent } from "@/components/chat/MarkdownContent";

export interface PracticeMessageBubbleProps {
  role: "user" | "sage-character" | "sage-hint";
  characterName?: string;
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

const ANIMATION_CONFIG = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.2 },
};

export function PracticeMessageBubble({
  role,
  characterName,
  content,
  timestamp,
  isStreaming = false,
}: PracticeMessageBubbleProps): JSX.Element {
  const isUser = role === "user";
  const isHint = role === "sage-hint";
  const formattedTime = formatTime(timestamp);

  // Hint message - centered, different style
  if (isHint) {
    return (
      <motion.div {...ANIMATION_CONFIG} className="flex justify-center w-full">
        <div className="px-4 py-2 text-sm italic text-amber-700 dark:text-amber-300 bg-amber-100/50 dark:bg-amber-900/30 rounded-lg border border-amber-200 dark:border-amber-800">
          <span className="font-medium not-italic">SAGE (hint):</span> {content}
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
            : "bg-amber-100 dark:bg-amber-900/30 text-slate-900 dark:text-slate-100 rounded-bl-md border border-amber-200 dark:border-amber-800"
        )}
      >
        {!isUser && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-amber-700 dark:text-amber-400">
              {characterName || "Character"}
            </span>
            <span className="text-xs text-amber-600/70 dark:text-amber-400/70">
              (SAGE)
            </span>
          </div>
        )}

        <div className="break-words">
          {isUser ? (
            <div className="whitespace-pre-wrap">{content}</div>
          ) : (
            <MarkdownContent content={content} />
          )}
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-amber-600 dark:bg-amber-400 animate-pulse" />
          )}
        </div>

        <div
          className={cn(
            "text-xs mt-2",
            isUser ? "text-sage-200" : "text-amber-600/70 dark:text-amber-400/70"
          )}
        >
          {formattedTime}
        </div>
      </div>
    </motion.div>
  );
}
