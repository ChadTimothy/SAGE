/**
 * Utility functions for SAGE frontend
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with clsx
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format a date for display
 */
export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format a timestamp for chat messages
 */
export function formatTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Capitalize first letter
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Format a dialogue mode for display (e.g., "outcome_check" -> "Outcome Check")
 */
export function formatDialogueMode(mode: string): string {
  return mode
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Truncate text with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + "...";
}

/**
 * Generate a random ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

/**
 * Delay utility for async operations
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Safe JSON parse with fallback
 */
export function safeJsonParse<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json);
  } catch {
    return fallback;
  }
}

/**
 * Convert energy level number to descriptive text for TTS
 */
function energyLevelToText(level: number): string {
  if (level < 40) return "low";
  if (level < 70) return "medium";
  return "high";
}

/**
 * Convert time available value to natural language
 */
function timeAvailableToText(time: string): string {
  const timeMap: Record<string, string> = {
    quick: "about 15 minutes",
    focused: "about 30 minutes",
    deep: "an hour or more",
  };
  return timeMap[time] || time;
}

/**
 * Format form data as a human-readable, TTS-friendly message.
 * This ensures form submissions appear sensibly in the chat feed
 * when read aloud to someone using voice output.
 */
export function formatFormDataAsMessage(
  formId: string,
  data: Record<string, unknown>
): string {
  const formIdLower = formId.toLowerCase();

  // Session check-in form
  if (formIdLower.includes("check_in") || formIdLower.includes("check-in")) {
    const parts: string[] = [];

    if (data.timeAvailable) {
      parts.push(`I have ${timeAvailableToText(String(data.timeAvailable))}`);
    }

    if (data.energyLevel !== undefined) {
      const level = Number(data.energyLevel);
      parts.push(`my energy is ${energyLevelToText(level)}`);
    }

    if (data.mindset) {
      parts.push(`and ${data.mindset}`);
    }

    return parts.length > 0 ? parts.join(", ") + "." : "Starting session.";
  }

  // Verification/quiz form
  if (formIdLower.includes("verification") || formIdLower.includes("quiz")) {
    if (data.answer !== undefined) {
      return `My answer is: ${data.answer}`;
    }
  }

  // Generic form - convert to natural key-value description
  const parts = Object.entries(data)
    .filter(([key, value]) => {
      // Skip internal fields and empty values
      if (key.startsWith("_")) return false;
      if (value === null || value === undefined || value === "") return false;
      return true;
    })
    .map(([key, value]) => {
      // Convert camelCase/snake_case to readable format
      const readableKey = key
        .replace(/([A-Z])/g, " $1")
        .replace(/_/g, " ")
        .toLowerCase()
        .trim();
      return `${readableKey}: ${value}`;
    });

  return parts.length > 0 ? parts.join(", ") : "Form submitted.";
}
