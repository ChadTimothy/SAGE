/**
 * Accessibility hooks for SAGE
 *
 * Part of #87 - Accessibility for Voice/UI Parity
 */

import { useEffect, useState, useCallback, useRef } from "react";
import {
  announceToScreenReader,
  focusFirstInteractive,
  prefersReducedMotion,
  handleKeyboardShortcut,
  getVoiceStatusMessage,
  type KeyboardShortcut,
} from "@/lib/accessibility";

/**
 * Hook to check if user prefers reduced motion
 */
export function useReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    setReducedMotion(prefersReducedMotion());

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);

    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  return reducedMotion;
}

/**
 * Hook for screen reader announcements.
 * Returns the announceToScreenReader function wrapped in useCallback for stable reference.
 */
export function useAnnounce(): typeof announceToScreenReader {
  return useCallback(
    (message: string, priority: "polite" | "assertive" = "polite") => {
      announceToScreenReader(message, priority);
    },
    []
  );
}

/**
 * Hook to manage focus when content changes
 */
export function useFocusManagement<T extends HTMLElement>() {
  const containerRef = useRef<T>(null);

  const focusFirst = useCallback(() => {
    focusFirstInteractive(containerRef.current);
  }, []);

  return { containerRef, focusFirst };
}

/**
 * Hook to announce voice status changes
 */
export function useVoiceStatusAnnouncement(status: string): void {
  const announce = useAnnounce();
  const previousStatus = useRef(status);

  useEffect(() => {
    if (status === previousStatus.current) return;

    const message = getVoiceStatusMessage(status);
    if (message) {
      const priority = status === "error" ? "assertive" : "polite";
      announce(message, priority);
    }

    previousStatus.current = status;
  }, [status, announce]);
}

/**
 * Hook for keyboard shortcuts
 */
export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      handleKeyboardShortcut(event, shortcuts);
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [shortcuts]);
}

/**
 * Hook to announce when UI components appear
 */
export function useUITreeAnnouncement(
  uiTree: { voice_fallback?: string } | null
) {
  const announce = useAnnounce();
  const previousTree = useRef<typeof uiTree>(null);

  useEffect(() => {
    // Only announce when a new tree appears
    if (uiTree && !previousTree.current) {
      const message = uiTree.voice_fallback
        ? `New form appeared: ${uiTree.voice_fallback}`
        : "A new form appeared";
      announce(message, "assertive");
    }
    previousTree.current = uiTree;
  }, [uiTree, announce]);
}

/**
 * Hook for modality switch announcements
 */
export function useModalityAnnouncement() {
  const announce = useAnnounce();

  const announceSwitch = useCallback(
    (from: "voice" | "form", to: "voice" | "form") => {
      const messages = {
        "voice-form": "Switched to form input. Use Tab to navigate fields.",
        "form-voice": "Switched to voice input. Speak your response.",
      };
      const key = `${from}-${to}` as keyof typeof messages;
      const message = messages[key];
      if (message) {
        announce(message, "polite");
      }
    },
    [announce]
  );

  return announceSwitch;
}
