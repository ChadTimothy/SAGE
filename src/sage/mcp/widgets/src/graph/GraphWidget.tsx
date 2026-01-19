import { useCallback, useEffect, useRef, useState } from 'react';
import { Network, Options, Data as VisData } from 'vis-network/standalone';
import { useOpenAi } from '../shared/hooks/useOpenAi';
import { useWidgetState } from '../shared/hooks/useWidgetState';
import type { GraphState, GraphResponse, GraphNode } from '../shared/types';

const INITIAL_STATE: GraphState = {
  lastFetched: undefined,
  data: undefined,
  selectedNodeId: undefined,
  filters: {
    nodeTypes: ['learner', 'outcome', 'concept', 'proof'],
    showEdges: true,
  },
};

const CACHE_DURATION = 5 * 60 * 1000;

// Node colors by type
const NODE_COLORS: Record<string, { background: string; border: string }> = {
  learner: { background: '#22c55e', border: '#16a34a' },
  outcome: { background: '#3b82f6', border: '#2563eb' },
  concept: { background: '#8b5cf6', border: '#7c3aed' },
  proof: { background: '#f59e0b', border: '#d97706' },
  session: { background: '#6b7280', border: '#4b5563' },
};

// Concept status colors
const STATUS_COLORS: Record<string, { background: string; border: string }> = {
  proven: { background: '#22c55e', border: '#16a34a' },
  explored: { background: '#3b82f6', border: '#2563eb' },
  identified: { background: '#9ca3af', border: '#6b7280' },
};

export function GraphWidget() {
  const { callTool, isReady, requestDisplayMode } = useOpenAi();
  const { state, setState } = useWidgetState<GraphState>(INITIAL_STATE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  const toggleFullscreen = useCallback(async () => {
    const newMode = isFullscreen ? 'inline' : 'fullscreen';
    try {
      const result = await requestDisplayMode(newMode);
      setIsFullscreen(result.mode === 'fullscreen');
    } catch (err) {
      console.error('Failed to change display mode:', err);
    }
  }, [isFullscreen, requestDisplayMode]);

  const fetchGraph = useCallback(async (force = false) => {
    if (!force && state.lastFetched && Date.now() - state.lastFetched < CACHE_DURATION) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await callTool<GraphResponse>('sage_graph');
      setState({
        data: result,
        lastFetched: Date.now(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph');
    } finally {
      setIsLoading(false);
    }
  }, [state.lastFetched, callTool, setState]);

  // Fetch on mount
  useEffect(() => {
    if (isReady) {
      fetchGraph();
    }
  }, [isReady, fetchGraph]);

  // Render network when data changes
  useEffect(() => {
    if (!containerRef.current || !state.data) return;

    const { nodes, edges } = state.data;
    const filters = state.filters;

    // Filter nodes by type
    const filteredNodes = nodes.filter((n) => filters?.nodeTypes.includes(n.type));
    const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));

    // Filter edges to only include those between visible nodes
    const filteredEdges = filters?.showEdges
      ? edges.filter((e) => filteredNodeIds.has(e.from) && filteredNodeIds.has(e.to))
      : [];

    // Convert to vis-network format
    const visNodes = filteredNodes.map((node) => {
      const colors = node.type === 'concept' && node.data.status
        ? STATUS_COLORS[node.data.status as string] || NODE_COLORS.concept
        : NODE_COLORS[node.type] || NODE_COLORS.concept;

      return {
        id: node.id,
        label: node.label,
        color: colors,
        shape: node.type === 'learner' ? 'dot' : 'box',
        size: node.type === 'learner' ? 20 : undefined,
        font: { color: '#1f2937', size: 12 },
      };
    });

    const visEdges = filteredEdges.map((edge) => ({
      id: edge.id,
      from: edge.from,
      to: edge.to,
      label: edge.label,
      arrows: 'to',
      color: { color: '#9ca3af', highlight: '#6b7280' },
      font: { size: 10, color: '#6b7280' },
    }));

    const data: VisData = { nodes: visNodes, edges: visEdges };

    const options: Options = {
      nodes: {
        borderWidth: 2,
        shadow: true,
        font: { face: 'system-ui, sans-serif' },
      },
      edges: {
        width: 1,
        smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
      },
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          springLength: 100,
        },
        stabilization: {
          iterations: 100,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
      },
    };

    // Destroy previous network
    if (networkRef.current) {
      networkRef.current.destroy();
    }

    // Create new network
    const network = new Network(containerRef.current, data, options);
    networkRef.current = network;

    // Handle node selection
    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = nodes.find((n) => n.id === nodeId);
        setSelectedNode(node || null);
        setState({ selectedNodeId: nodeId });
      } else {
        setSelectedNode(null);
        setState({ selectedNodeId: undefined });
      }
    });

    return () => {
      network.destroy();
    };
  }, [state.data, state.filters, setState]);

  const toggleNodeType = (type: string) => {
    const current = state.filters?.nodeTypes || [];
    const next = current.includes(type)
      ? current.filter((t) => t !== type)
      : [...current, type];
    setState({ filters: { ...state.filters, nodeTypes: next, showEdges: state.filters?.showEdges ?? true } });
  };

  if (!isReady || (isLoading && !state.data)) {
    return (
      <div className="widget-container flex items-center justify-center">
        <div className="text-gray-500">Loading graph...</div>
      </div>
    );
  }

  if (error && !state.data) {
    return (
      <div className="widget-container">
        <div className="widget-card text-center">
          <p className="text-red-500 mb-2">{error}</p>
          <button onClick={() => fetchGraph(true)} className="widget-btn widget-btn-secondary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="widget-container">
      <div className="widget-card p-2">
        {/* Header */}
        <div className="flex justify-between items-center mb-2 px-2">
          <h2 className="text-sm font-semibold">Knowledge Graph</h2>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">
              {state.data?.node_count} nodes, {state.data?.edge_count} edges
            </span>
            <button
              onClick={() => fetchGraph(true)}
              disabled={isLoading}
              className="text-xs text-sage-600 hover:text-sage-700 disabled:opacity-50"
              title="Refresh"
            >
              {isLoading ? '...' : '↻'}
            </button>
            <button
              onClick={toggleFullscreen}
              className="text-xs text-sage-600 hover:text-sage-700"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? '⤓' : '⤢'}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-1 mb-2 px-2">
          {['learner', 'outcome', 'concept', 'proof'].map((type) => (
            <button
              key={type}
              onClick={() => toggleNodeType(type)}
              className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                state.filters?.nodeTypes.includes(type)
                  ? 'bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-400'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        {/* Graph container */}
        <div
          ref={containerRef}
          className={`${isFullscreen ? 'h-96' : 'h-64'} bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 transition-all duration-300`}
        />

        {/* Selected node details */}
        {selectedNode && (
          <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-sm">
            <div className="font-medium">{selectedNode.label}</div>
            <div className="text-xs text-gray-500">
              Type: {selectedNode.type}
              {typeof selectedNode.data.status === 'string' && ` • Status: ${selectedNode.data.status}`}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
