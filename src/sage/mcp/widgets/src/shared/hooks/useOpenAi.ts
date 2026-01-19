import { useCallback, useEffect, useState } from 'react';
import type { OpenAIClient, DisplayMode, DisplayModeResult, ToolCallResult } from '../types';

/**
 * Hook to access the ChatGPT App SDK (window.openai)
 * Based on https://developers.openai.com/apps-sdk
 */
export function useOpenAi() {
  const [client, setClient] = useState<OpenAIClient | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Check if window.openai exists (production in ChatGPT)
    if (window.openai) {
      setClient(window.openai);
      setIsReady(true);
      return;
    }

    // In development, create a mock client
    if (import.meta.env.DEV) {
      const mockClient = createMockClient();
      setClient(mockClient);
      setIsReady(true);
      console.log('[SAGE Widget] Using mock OpenAI client for development');
      return;
    }

    // Production without window.openai is an error
    setError(new Error('window.openai not available'));
  }, []);

  const callTool = useCallback(
    async <T = unknown>(name: string, args?: Record<string, unknown>): Promise<T> => {
      if (!client) {
        throw new Error('OpenAI client not ready');
      }
      const result = await client.callTool<T>(name, args);
      return result.result;
    },
    [client]
  );

  const setWidgetState = useCallback(
    <T extends object>(payload: T): void => {
      client?.setWidgetState(payload);
    },
    [client]
  );

  const getWidgetState = useCallback(
    <T = unknown>(): T | undefined => {
      return client?.widgetState as T | undefined;
    },
    [client]
  );

  const requestDisplayMode = useCallback(
    async (mode: DisplayMode): Promise<DisplayModeResult> => {
      if (!client) {
        throw new Error('OpenAI client not ready');
      }
      return client.requestDisplayMode({ mode });
    },
    [client]
  );

  const requestClose = useCallback((): void => {
    client?.requestClose();
  }, [client]);

  const sendFollowUp = useCallback(
    async (prompt: string): Promise<void> => {
      if (!client) {
        throw new Error('OpenAI client not ready');
      }
      await client.sendFollowUpMessage({ prompt });
    },
    [client]
  );

  const openExternal = useCallback(
    (href: string): void => {
      client?.openExternal({ href });
    },
    [client]
  );

  return {
    client,
    isReady,
    error,
    callTool,
    setWidgetState,
    getWidgetState,
    requestDisplayMode,
    requestClose,
    sendFollowUp,
    openExternal,
  };
}

/**
 * Create a mock client for development/testing
 */
function createMockClient(): OpenAIClient {
  let mockState: unknown = undefined;

  return {
    async callTool<T>(name: string, args?: Record<string, unknown>): Promise<ToolCallResult<T>> {
      console.log(`[Mock] callTool: ${name}`, args);

      // Simulate network delay
      await new Promise((r) => setTimeout(r, 300));

      // Return mock responses based on tool name
      const result = getMockResponse(name, args) as T;
      return { result, structuredContent: {} };
    },

    setWidgetState<T extends object>(payload: T): void {
      mockState = payload;
      console.log('[Mock] setWidgetState:', payload);
    },

    get widgetState() {
      return mockState;
    },

    async requestDisplayMode(options: { mode: DisplayMode }): Promise<DisplayModeResult> {
      console.log(`[Mock] requestDisplayMode: ${options.mode}`);
      // In mock, we grant the requested mode (may differ on mobile)
      return { mode: options.mode };
    },

    requestClose(): void {
      console.log('[Mock] requestClose');
    },

    async sendFollowUpMessage(options: { prompt: string }): Promise<void> {
      console.log(`[Mock] sendFollowUpMessage: ${options.prompt}`);
    },

    openExternal(options: { href: string }): void {
      console.log(`[Mock] openExternal: ${options.href}`);
      // In development, actually open the link
      window.open(options.href, '_blank');
    },
  };
}

/**
 * Generate mock responses for different MCP tools
 */
function getMockResponse(name: string, args?: Record<string, unknown>): unknown {
  switch (name) {
    case 'sage_start_session':
      return {
        session_id: 'mock-session-123',
        message: 'Welcome back! How are you showing up today?',
        learner_created: false,
      };

    case 'sage_checkin':
      return {
        adaptations: [
          'Shorter explanations for quick session',
          'Focus on practical exercises',
        ],
        session_context: {
          energy: args?.energy || 'medium',
          time_available: args?.time_available || 'normal',
          mindset: args?.mindset || 'focused',
        },
        message: "Got it! I'll adapt our session accordingly.",
      };

    case 'sage_progress':
      return {
        total_sessions: 12,
        total_proofs: 8,
        recent_concepts: [
          { id: 'c1', name: 'python_basics', display_name: 'Python Basics', status: 'proven', proof_count: 2 },
          { id: 'c2', name: 'functions', display_name: 'Functions', status: 'explored', proof_count: 1 },
          { id: 'c3', name: 'loops', display_name: 'Loops', status: 'identified', proof_count: 0 },
        ],
        active_outcomes: [
          { id: 'o1', description: 'Build a web scraper', status: 'active', progress_percentage: 45 },
        ],
      };

    case 'sage_graph':
      return {
        nodes: [
          { id: 'l1', type: 'learner', label: 'You', data: {} },
          { id: 'o1', type: 'outcome', label: 'Build a web scraper', data: { status: 'active' } },
          { id: 'c1', type: 'concept', label: 'Python Basics', data: { status: 'proven' } },
          { id: 'c2', type: 'concept', label: 'Functions', data: { status: 'explored' } },
          { id: 'c3', type: 'concept', label: 'Loops', data: { status: 'identified' } },
          { id: 'p1', type: 'proof', label: 'Proof: Python Basics', data: {} },
        ],
        edges: [
          { id: 'e1', from: 'l1', to: 'o1', type: 'pursuing' },
          { id: 'e2', from: 'o1', to: 'c1', type: 'requires' },
          { id: 'e3', from: 'o1', to: 'c2', type: 'requires' },
          { id: 'e4', from: 'o1', to: 'c3', type: 'requires' },
          { id: 'e5', from: 'c1', to: 'p1', type: 'demonstrated_by' },
          { id: 'e6', from: 'c2', to: 'c1', type: 'builds_on' },
        ],
        node_count: 6,
        edge_count: 6,
      };

    case 'sage_practice_start':
      return {
        practice_id: 'practice-mock-456',
        scenario: {
          title: 'Debug a Python Script',
          description: 'A client has sent you a buggy Python script. Find and fix the issues.',
          sage_role: 'Client who wrote the code',
          user_role: 'Developer helping debug',
        },
        concept: 'Python Debugging',
        opening_message: "Hey, thanks for helping! My script keeps crashing when I try to process a list. Here's what happens...",
      };

    case 'sage_practice_respond':
      return {
        feedback: "Good approach! You correctly identified that the index was out of bounds.",
        score: 75,
        areas_good: ['Problem identification', 'Clear explanation'],
        areas_improve: ['Could suggest a more defensive approach'],
        suggestions: ['Consider using try/except for index errors'],
        continue_practice: true,
      };

    case 'sage_practice_end':
      return {
        practice_complete: true,
        summary: 'You successfully debugged the script and explained the fix clearly.',
        key_learnings: [
          'Always check list bounds before indexing',
          'Use defensive programming patterns',
        ],
        proof_created: true,
        proof_id: 'proof-mock-789',
      };

    default:
      console.warn(`[Mock] Unknown tool: ${name}`);
      return { error: `Unknown tool: ${name}` };
  }
}
