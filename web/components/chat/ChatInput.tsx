"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { VoiceWaveform } from "@/components/voice";

export interface ChatInputProps {
  onSend: (message: string) => void;
  onVoiceStart?: () => void;
  onVoiceEnd?: () => void;
  isListening?: boolean;
  disabled?: boolean;
  placeholder?: string;
  audioLevel?: number;
  interimTranscript?: string;
}

export function ChatInput({
  onSend,
  onVoiceStart,
  onVoiceEnd,
  isListening = false,
  disabled = false,
  placeholder = "Type a message...",
  audioLevel = 0,
  interimTranscript = "",
}: ChatInputProps): JSX.Element {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [message]);

  function handleSubmit(e: React.FormEvent): void {
    e.preventDefault();
    if (!message.trim() || disabled) return;

    onSend(message.trim());
    setMessage("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: React.KeyboardEvent): void {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleVoiceToggle(): void {
    if (isListening) {
      onVoiceEnd?.();
    } else {
      onVoiceStart?.();
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 p-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
    >
      <div className="flex-shrink-0 flex items-center gap-2">
        <button
          type="button"
          onClick={handleVoiceToggle}
          disabled={disabled}
          className={cn(
            "p-3 rounded-full transition-colors",
            isListening
              ? "bg-red-500 text-white hover:bg-red-600"
              : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          aria-label={isListening ? "Stop recording" : "Start voice input"}
        >
          {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>
        {isListening && (
          <VoiceWaveform audioLevel={audioLevel} isActive={isListening} />
        )}
      </div>

      <div className="flex-1">
        <textarea
          ref={textareaRef}
          value={isListening && interimTranscript ? interimTranscript : message}
          onChange={(e) => !isListening && setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? "Listening..." : placeholder}
          disabled={disabled || isListening}
          rows={1}
          className={cn(
            "w-full resize-none rounded-2xl px-4 py-3",
            "bg-slate-100 dark:bg-slate-800",
            "text-slate-900 dark:text-slate-100",
            "placeholder:text-slate-500 dark:placeholder:text-slate-400",
            "focus:outline-none focus:ring-2 focus:ring-sage-500",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "max-h-[150px]",
            isListening && "italic text-slate-500"
          )}
        />
      </div>

      <button
        type="submit"
        disabled={disabled || !message.trim()}
        className={cn(
          "flex-shrink-0 p-3 rounded-full transition-colors",
          "bg-sage-600 text-white hover:bg-sage-700",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-sage-600"
        )}
        aria-label="Send message"
      >
        <Send className="h-5 w-5" />
      </button>
    </form>
  );
}
