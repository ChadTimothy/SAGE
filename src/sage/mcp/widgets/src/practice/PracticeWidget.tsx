import { useCallback, useRef, useState, useEffect } from 'react';
import { useOpenAi } from '../shared/hooks/useOpenAi';
import { useWidgetState } from '../shared/hooks/useWidgetState';
import type {
  PracticeState,
  PracticeMessage,
  PracticeStartResponse,
  PracticeRespondResponse,
  PracticeEndResponse,
} from '../shared/types';

const INITIAL_STATE: PracticeState = {
  practiceId: undefined,
  scenario: undefined,
  messages: [],
  score: undefined,
  completed: false,
};

export function PracticeWidget() {
  const { callTool, isReady } = useOpenAi();
  const { state, setState, resetState } = useWidgetState<PracticeState>(INITIAL_STATE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [feedback, setFeedback] = useState<PracticeRespondResponse | null>(null);
  const [summary, setSummary] = useState<PracticeEndResponse | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages]);

  const startPractice = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await callTool<PracticeStartResponse>('sage_practice_start', {
        scenario_type: 'realistic',
      });

      const initialMessage: PracticeMessage = {
        role: 'sage',
        content: result.opening_message,
        timestamp: Date.now(),
      };

      setState({
        practiceId: result.practice_id,
        scenario: result.scenario,
        messages: [initialMessage],
        completed: false,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start practice');
    } finally {
      setIsLoading(false);
    }
  }, [callTool, setState]);

  const sendResponse = useCallback(async () => {
    if (!inputValue.trim() || !state.practiceId) return;

    const userMessage: PracticeMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: Date.now(),
    };

    setState({
      messages: [...state.messages, userMessage],
    });
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const result = await callTool<PracticeRespondResponse>('sage_practice_respond', {
        practice_id: state.practiceId,
        response: userMessage.content,
      });

      setFeedback(result);
      setState({ score: result.score });

      // Add SAGE's feedback as a message
      const sageMessage: PracticeMessage = {
        role: 'sage',
        content: result.feedback,
        timestamp: Date.now(),
      };
      setState({
        messages: [...state.messages, userMessage, sageMessage],
      });

      if (!result.continue_practice) {
        setState({ completed: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send response');
    } finally {
      setIsLoading(false);
    }
  }, [inputValue, state.practiceId, state.messages, callTool, setState]);

  const endPractice = useCallback(async () => {
    if (!state.practiceId) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await callTool<PracticeEndResponse>('sage_practice_end', {
        practice_id: state.practiceId,
        self_reflection: 'Completed the practice session',
      });

      setSummary(result);
      setState({ completed: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to end practice');
    } finally {
      setIsLoading(false);
    }
  }, [state.practiceId, callTool, setState]);

  const handleNewPractice = useCallback(() => {
    resetState();
    setFeedback(null);
    setSummary(null);
    setError(null);
  }, [resetState]);

  if (!isReady) {
    return (
      <div className="widget-container flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  // Summary view after completion
  if (summary) {
    return (
      <div className="widget-container">
        <div className="widget-card">
          <h2 className="text-lg font-semibold text-sage-600 mb-3">Practice Complete!</h2>

          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">{summary.summary}</p>

          {summary.key_learnings.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium mb-2">Key Learnings:</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                {summary.key_learnings.map((learning, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-sage-500">•</span>
                    {learning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.proof_created && (
            <div className="mb-4 p-2 bg-sage-50 dark:bg-sage-900/20 rounded text-sm text-sage-700 dark:text-sage-400">
              Proof earned for this concept!
            </div>
          )}

          <button onClick={handleNewPractice} className="w-full widget-btn widget-btn-primary">
            Start New Practice
          </button>
        </div>
      </div>
    );
  }

  // Start view
  if (!state.practiceId) {
    return (
      <div className="widget-container">
        <div className="widget-card text-center">
          <h2 className="text-lg font-semibold mb-2">Practice Mode</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Apply what you've learned in realistic scenarios. SAGE will roleplay with you and provide feedback.
          </p>

          {error && (
            <div className="mb-4 p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded">
              {error}
            </div>
          )}

          <button
            onClick={startPractice}
            disabled={isLoading}
            className="widget-btn widget-btn-primary disabled:opacity-50"
          >
            {isLoading ? 'Starting...' : 'Start Practice'}
          </button>
        </div>
      </div>
    );
  }

  // Active practice view
  return (
    <div className="widget-container">
      <div className="widget-card flex flex-col h-[460px]">
        {/* Scenario header */}
        {state.scenario && (
          <div className="mb-3 pb-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold">{state.scenario.title}</h3>
            <p className="text-xs text-gray-500 mt-1">
              You: {state.scenario.user_role} | SAGE: {state.scenario.sage_role}
            </p>
            {state.score !== undefined && (
              <div className="mt-1 text-xs text-sage-600">Current score: {state.score}%</div>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-3 mb-3">
          {state.messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Feedback panel */}
        {feedback && !state.completed && (
          <FeedbackPanel feedback={feedback} onDismiss={() => setFeedback(null)} />
        )}

        {/* Error */}
        {error && (
          <div className="mb-2 p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-xs rounded">
            {error}
          </div>
        )}

        {/* Input area */}
        {!state.completed ? (
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !isLoading && sendResponse()}
              placeholder="Type your response..."
              disabled={isLoading}
              className="flex-1 widget-input text-sm"
            />
            <button
              onClick={sendResponse}
              disabled={isLoading || !inputValue.trim()}
              className="widget-btn widget-btn-primary text-sm disabled:opacity-50"
            >
              {isLoading ? '...' : 'Send'}
            </button>
            <button
              onClick={endPractice}
              disabled={isLoading}
              className="widget-btn widget-btn-secondary text-sm disabled:opacity-50"
            >
              End
            </button>
          </div>
        ) : (
          <button onClick={endPractice} className="w-full widget-btn widget-btn-primary">
            View Summary
          </button>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: PracticeMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? 'bg-sage-500 text-white'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}

function FeedbackPanel({
  feedback,
  onDismiss,
}: {
  feedback: PracticeRespondResponse;
  onDismiss: () => void;
}) {
  return (
    <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs">
      <div className="flex justify-between items-start mb-1">
        <span className="font-medium text-blue-700 dark:text-blue-400">Feedback</span>
        <button onClick={onDismiss} className="text-blue-400 hover:text-blue-600">
          ×
        </button>
      </div>

      {feedback.areas_good.length > 0 && (
        <div className="text-green-600 dark:text-green-400">
          Good: {feedback.areas_good.join(', ')}
        </div>
      )}

      {feedback.areas_improve.length > 0 && (
        <div className="text-orange-600 dark:text-orange-400">
          Improve: {feedback.areas_improve.join(', ')}
        </div>
      )}
    </div>
  );
}
