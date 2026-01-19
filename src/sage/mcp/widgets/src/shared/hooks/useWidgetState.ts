import { useCallback, useEffect, useState } from 'react';
import { useOpenAi } from './useOpenAi';

/**
 * Hook to manage persistent widget state via window.openai.setWidgetState
 * State persists across widget remounts and is exposed to ChatGPT model
 *
 * Based on https://developers.openai.com/apps-sdk/build/chatgpt-ui
 *
 * Note: State is scoped to the specific widget instance (message_id/widgetId pair).
 * Keep payload under 4k tokens for performance.
 */
export function useWidgetState<T extends object>(initialState: T) {
  const { setWidgetState, getWidgetState, isReady } = useOpenAi();
  const [state, setLocalState] = useState<T>(initialState);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load persisted state on mount
  useEffect(() => {
    if (!isReady) return;

    const persisted = getWidgetState<T>();
    if (persisted) {
      setLocalState(persisted);
    }
    setIsLoaded(true);
  }, [isReady, getWidgetState]);

  // Update both local and persisted state
  const setState = useCallback(
    (update: Partial<T> | ((prev: T) => T)) => {
      setLocalState((prev) => {
        const next = typeof update === 'function' ? update(prev) : { ...prev, ...update };
        // Persist to OpenAI state (exposed to ChatGPT model)
        setWidgetState(next);
        return next;
      });
    },
    [setWidgetState]
  );

  // Reset to initial state
  const resetState = useCallback(() => {
    setLocalState(initialState);
    setWidgetState(initialState);
  }, [initialState, setWidgetState]);

  return {
    state,
    setState,
    resetState,
    isLoaded,
  };
}
