/**
 * Accessibility utilities for SAGE
 *
 * Part of #87 - Accessibility for Voice/UI Parity
 */

/**
 * Announce a message to screen readers via ARIA live region
 */
export function announceToScreenReader(
  message: string,
  priority: "polite" | "assertive" = "polite"
): void {
  // Find or create the announcer element
  let announcer = document.getElementById("sr-announcer");

  if (!announcer) {
    announcer = document.createElement("div");
    announcer.id = "sr-announcer";
    announcer.setAttribute("role", "status");
    announcer.setAttribute("aria-live", priority);
    announcer.setAttribute("aria-atomic", "true");
    announcer.className = "sr-only";
    document.body.appendChild(announcer);
  }

  // Update priority if different
  announcer.setAttribute("aria-live", priority);

  // Clear and set new message (triggers announcement)
  announcer.textContent = "";
  // Use setTimeout to ensure the clear happens before the new message
  setTimeout(() => {
    if (announcer) {
      announcer.textContent = message;
    }
  }, 100);
}

/**
 * Focus the first interactive element in a container
 */
export function focusFirstInteractive(container: HTMLElement | null): void {
  if (!container) return;

  const selectors = [
    "input:not([disabled])",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "select:not([disabled])",
    '[tabindex]:not([tabindex="-1"])',
    "a[href]",
  ].join(", ");

  const firstInteractive = container.querySelector<HTMLElement>(selectors);
  if (firstInteractive) {
    firstInteractive.focus();
  }
}

/**
 * Generate unique IDs for form elements
 */
let idCounter = 0;
export function generateId(prefix: string = "sage"): string {
  return `${prefix}-${++idCounter}`;
}

/**
 * Hook to check if user prefers reduced motion
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Voice status labels for screen readers
 */
export const VOICE_STATUS_LABELS: Record<string, string> = {
  idle: "Voice input idle",
  connecting: "Connecting to voice service",
  connected: "Voice service connected, ready to listen",
  listening: "Listening for voice input",
  speaking: "SAGE is speaking",
  reconnecting: "Reconnecting to voice service",
  error: "Voice error occurred",
  fallback: "Voice unavailable, using text input",
};

/**
 * Get accessible label for voice status
 */
export function getVoiceStatusLabel(status: string): string {
  return VOICE_STATUS_LABELS[status] || `Voice status: ${status}`;
}

/**
 * Keyboard shortcut handler
 */
export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
  handler: () => void;
  description: string;
}

export function handleKeyboardShortcut(
  event: KeyboardEvent,
  shortcuts: KeyboardShortcut[]
): boolean {
  for (const shortcut of shortcuts) {
    if (
      event.key.toLowerCase() === shortcut.key.toLowerCase() &&
      (!shortcut.ctrlKey || event.ctrlKey) &&
      (!shortcut.shiftKey || event.shiftKey) &&
      (!shortcut.altKey || event.altKey) &&
      (!shortcut.metaKey || event.metaKey)
    ) {
      event.preventDefault();
      shortcut.handler();
      return true;
    }
  }
  return false;
}

/**
 * Format keyboard shortcut for display
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = [];
  if (shortcut.ctrlKey) parts.push("Ctrl");
  if (shortcut.shiftKey) parts.push("Shift");
  if (shortcut.altKey) parts.push("Alt");
  if (shortcut.metaKey) parts.push("Cmd");
  parts.push(shortcut.key.toUpperCase());
  return parts.join("+");
}
