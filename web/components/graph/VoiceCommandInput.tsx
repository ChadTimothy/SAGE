"use client";

import { useState, useCallback } from "react";
import { Mic, MicOff, Send, Loader2 } from "lucide-react";
import type { GraphFilterUpdate } from "@/types";

interface VoiceCommandInputProps {
  onFilterUpdate: (filters: GraphFilterUpdate) => void;
}

export function VoiceCommandInput({ onFilterUpdate }: VoiceCommandInputProps): JSX.Element {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractFilters = useCallback(async (text: string) => {
    if (!text.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/graph/extract-filters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error("Failed to process command");
      }

      const data = await response.json();

      if (data.success && data.filters) {
        onFilterUpdate(data.filters);
        setInput("");
      } else {
        setError("Could not understand the filter command");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  }, [onFilterUpdate]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    extractFilters(input);
  }, [input, extractFilters]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      // Stop listening
      setIsListening(false);
      if (window.speechRecognition) {
        window.speechRecognition.stop();
      }
    } else {
      // Start listening using Web Speech API
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setError("Speech recognition not supported in this browser");
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        extractFilters(transcript);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        setError(`Speech recognition error: ${event.error}`);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      window.speechRecognition = recognition;
      recognition.start();
      setIsListening(true);
      setError(null);
    }
  }, [isListening, extractFilters]);

  return (
    <div className="flex flex-col gap-2">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Filter by voice: 'show only proven concepts'"
            className="w-full px-3 py-2 pr-10 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            disabled={isLoading}
          />
          {isLoading && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-slate-400" />
          )}
        </div>

        <button
          type="button"
          onClick={toggleListening}
          className={`p-2 rounded-lg transition-colors ${
            isListening
              ? "bg-red-500 text-white hover:bg-red-600"
              : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
          }`}
          title={isListening ? "Stop listening" : "Start voice command"}
        >
          {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>

        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="p-2 rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Apply filter"
        >
          <Send className="h-5 w-5" />
        </button>
      </form>

      {error && (
        <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
      )}

      <p className="text-xs text-slate-500 dark:text-slate-400">
        Try: &quot;show only proven&quot;, &quot;hide outcomes&quot;, &quot;filter by pricing&quot;, &quot;show everything&quot;
      </p>
    </div>
  );
}

// Extend Window interface for Speech Recognition
declare global {
  interface Window {
    SpeechRecognition?: typeof SpeechRecognition;
    webkitSpeechRecognition?: typeof SpeechRecognition;
    speechRecognition?: SpeechRecognition;
  }
}
