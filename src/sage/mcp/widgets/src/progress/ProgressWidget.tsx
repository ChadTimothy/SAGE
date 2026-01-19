import { useCallback, useEffect, useState } from 'react';
import { useOpenAi } from '../shared/hooks/useOpenAi';
import { useWidgetState } from '../shared/hooks/useWidgetState';
import type { ProgressState, ProgressResponse, ConceptSummary, OutcomeSummary } from '../shared/types';

const INITIAL_STATE: ProgressState = {
  lastFetched: undefined,
  data: undefined,
};

// Cache for 5 minutes
const CACHE_DURATION = 5 * 60 * 1000;

export function ProgressWidget() {
  const { callTool, isReady } = useOpenAi();
  const { state, setState } = useWidgetState<ProgressState>(INITIAL_STATE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProgress = useCallback(async (force = false) => {
    // Use cache if fresh enough
    if (!force && state.lastFetched && Date.now() - state.lastFetched < CACHE_DURATION) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await callTool<ProgressResponse>('sage_progress');
      setState({
        data: result,
        lastFetched: Date.now(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load progress');
    } finally {
      setIsLoading(false);
    }
  }, [state.lastFetched, callTool, setState]);

  // Fetch on mount
  useEffect(() => {
    if (isReady) {
      fetchProgress();
    }
  }, [isReady, fetchProgress]);

  if (!isReady || (isLoading && !state.data)) {
    return (
      <div className="widget-container flex items-center justify-center">
        <div className="text-gray-500">Loading progress...</div>
      </div>
    );
  }

  if (error && !state.data) {
    return (
      <div className="widget-container">
        <div className="widget-card text-center">
          <p className="text-red-500 mb-2">{error}</p>
          <button onClick={() => fetchProgress(true)} className="widget-btn widget-btn-secondary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { data } = state;
  if (!data) return null;

  return (
    <div className="widget-container">
      <div className="widget-card">
        {/* Header with refresh */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Your Progress</h2>
          <button
            onClick={() => fetchProgress(true)}
            disabled={isLoading}
            className="text-sm text-sage-600 hover:text-sage-700 disabled:opacity-50"
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <StatCard label="Sessions" value={data.total_sessions} />
          <StatCard label="Proofs Earned" value={data.total_proofs} />
        </div>

        {/* Active Outcomes */}
        {data.active_outcomes.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-medium mb-2">Active Goals</h3>
            <div className="space-y-2">
              {data.active_outcomes.map((outcome) => (
                <OutcomeCard key={outcome.id} outcome={outcome} />
              ))}
            </div>
          </div>
        )}

        {/* Recent Concepts */}
        {data.recent_concepts.length > 0 && (
          <div>
            <h3 className="text-sm font-medium mb-2">Recent Concepts</h3>
            <div className="space-y-1">
              {data.recent_concepts.slice(0, 5).map((concept) => (
                <ConceptRow key={concept.id} concept={concept} />
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {data.active_outcomes.length === 0 && data.recent_concepts.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            Start a learning session to track your progress!
          </p>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
      <div className="text-2xl font-bold text-sage-600">{value}</div>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
    </div>
  );
}

function OutcomeCard({ outcome }: { outcome: OutcomeSummary }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
      <div className="flex justify-between items-start mb-2">
        <span className="text-sm font-medium">{outcome.description}</span>
        <span className="text-xs text-sage-600 font-medium">{outcome.progress_percentage}%</span>
      </div>
      <div className="h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
        <div
          className="h-full bg-sage-500 rounded-full transition-all duration-300"
          style={{ width: `${outcome.progress_percentage}%` }}
        />
      </div>
    </div>
  );
}

function ConceptRow({ concept }: { concept: ConceptSummary }) {
  const statusColors: Record<string, string> = {
    proven: 'bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-400',
    explored: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    identified: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  };

  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700/30">
      <span className="text-sm">{concept.display_name}</span>
      <div className="flex items-center gap-2">
        {concept.proof_count > 0 && (
          <span className="text-xs text-gray-400">{concept.proof_count} proof{concept.proof_count !== 1 ? 's' : ''}</span>
        )}
        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[concept.status] || statusColors.identified}`}>
          {concept.status}
        </span>
      </div>
    </div>
  );
}
