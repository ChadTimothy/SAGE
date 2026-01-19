import { useCallback, useState } from 'react';
import { useOpenAi } from '../shared/hooks/useOpenAi';
import { useWidgetState } from '../shared/hooks/useWidgetState';
import type { CheckinState, CheckinResponse } from '../shared/types';

type EnergyLevel = 'low' | 'medium' | 'high';
type TimeAvailable = 'quick' | 'normal' | 'deep';

const INITIAL_STATE: CheckinState = {
  energy: undefined,
  timeAvailable: undefined,
  mindset: undefined,
  setting: undefined,
  submitted: false,
};

export function CheckinWidget() {
  const { callTool, isReady } = useOpenAi();
  const { state, setState } = useWidgetState<CheckinState>(INITIAL_STATE);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [response, setResponse] = useState<CheckinResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!state.energy || !state.timeAvailable) {
      setError('Please select your energy level and available time');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await callTool<CheckinResponse>('sage_checkin', {
        energy: state.energy,
        time_available: state.timeAvailable,
        mindset: state.mindset,
        setting: state.setting,
      });

      setResponse(result);
      setState({ submitted: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit check-in');
    } finally {
      setIsSubmitting(false);
    }
  }, [state, callTool, setState]);

  if (!isReady) {
    return (
      <div className="widget-container flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (state.submitted && response) {
    return (
      <div className="widget-container">
        <div className="widget-card">
          <h2 className="text-lg font-semibold mb-3 text-sage-600">Ready to Learn!</h2>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">{response.message}</p>

          {response.adaptations.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium mb-2">Session Adaptations:</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                {response.adaptations.map((adapt, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-sage-500">•</span>
                    {adapt}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="widget-container">
      <div className="widget-card">
        <h2 className="text-lg font-semibold mb-4">How are you showing up today?</h2>

        {/* Energy Level */}
        <div className="mb-4">
          <label className="widget-label">Energy Level</label>
          <div className="flex gap-2">
            {(['low', 'medium', 'high'] as EnergyLevel[]).map((level) => (
              <button
                key={level}
                onClick={() => setState({ energy: level })}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                  state.energy === level
                    ? 'bg-sage-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {level === 'low' && '😴 Low'}
                {level === 'medium' && '🙂 Medium'}
                {level === 'high' && '⚡ High'}
              </button>
            ))}
          </div>
        </div>

        {/* Time Available */}
        <div className="mb-4">
          <label className="widget-label">Time Available</label>
          <div className="flex gap-2">
            {(['quick', 'normal', 'deep'] as TimeAvailable[]).map((time) => (
              <button
                key={time}
                onClick={() => setState({ timeAvailable: time })}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                  state.timeAvailable === time
                    ? 'bg-sage-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {time === 'quick' && '⏱️ Quick (15m)'}
                {time === 'normal' && '🕐 Normal (30-60m)'}
                {time === 'deep' && '🧘 Deep (1h+)'}
              </button>
            ))}
          </div>
        </div>

        {/* Mindset (optional) */}
        <div className="mb-4">
          <label className="widget-label">
            Mindset <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            placeholder="e.g., curious, stressed about deadline, excited to learn"
            value={state.mindset || ''}
            onChange={(e) => setState({ mindset: e.target.value })}
            className="widget-input"
          />
        </div>

        {/* Setting (optional) */}
        <div className="mb-4">
          <label className="widget-label">
            Environment <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            placeholder="e.g., quiet office, commuting, home evening"
            value={state.setting || ''}
            onChange={(e) => setState({ setting: e.target.value })}
            className="widget-input"
          />
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded">
            {error}
          </div>
        )}

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="w-full widget-btn widget-btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Checking in...' : "Let's Go!"}
        </button>
      </div>
    </div>
  );
}
