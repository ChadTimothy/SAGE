"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Send, Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";

export default function ChatPage(): React.ReactElement {
  const [message, setMessage] = useState("");
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    // TODO: Send message via WebSocket
    console.log("Send:", message);
    setMessage("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            Chat with SAGE
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Tell me what you want to learn
          </p>
        </div>
        <button
          onClick={() => setIsVoiceEnabled(!isVoiceEnabled)}
          className={cn(
            "p-3 rounded-full transition-colors",
            isVoiceEnabled
              ? "bg-sage-100 text-sage-600 dark:bg-sage-900 dark:text-sage-400"
              : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
          )}
          aria-label={isVoiceEnabled ? "Disable voice" : "Enable voice"}
        >
          {isVoiceEnabled ? (
            <Mic className="h-5 w-5" />
          ) : (
            <MicOff className="h-5 w-5" />
          )}
        </button>
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Welcome message */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex gap-4"
        >
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-sage-100 dark:bg-sage-900 flex items-center justify-center">
            <span className="text-sage-600 dark:text-sage-400 font-semibold">
              S
            </span>
          </div>
          <div className="flex-1 bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
            <p className="text-slate-700 dark:text-slate-300">
              Welcome! I&apos;m SAGE, your AI tutor. What do you want to be able to
              DO? Tell me your goal, and we&apos;ll figure out how to get you there.
            </p>
          </div>
        </motion.div>

        {/* Placeholder for messages */}
        <div className="text-center text-slate-400 py-8">
          <p>Start a conversation to begin learning</p>
        </div>
      </div>

      {/* Input area */}
      <form
        onSubmit={handleSubmit}
        className="p-4 border-t border-slate-200 dark:border-slate-800"
      >
        <div className="flex gap-4 max-w-4xl mx-auto">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 px-4 py-3 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-sage-500 text-slate-900 dark:text-white placeholder-slate-400"
          />
          <button
            type="submit"
            disabled={!message.trim()}
            className="px-6 py-3 bg-sage-600 text-white rounded-lg hover:bg-sage-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </form>
    </div>
  );
}
