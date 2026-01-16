"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { Network, ZoomIn, ZoomOut, RefreshCw, AlertCircle } from "lucide-react";
import { useSessionLearner } from "@/hooks/useSessionLearner";
import { api } from "@/lib/api";
import { NodeDetailPanel, GraphFilters, VoiceCommandInput } from "@/components/graph";
import type {
  KnowledgeNode,
  KnowledgeNodeStatus,
  KnowledgeEdge,
  GraphFilterState,
  GraphFilterUpdate,
  OutcomeSnapshot,
  LearnerGraph,
} from "@/types";

// Dynamic import to avoid SSR issues with vis-network
const KnowledgeGraph = dynamic(
  () => import("@/components/graph/KnowledgeGraph").then((mod) => mod.KnowledgeGraph),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-500">Loading graph...</div>
      </div>
    ),
  }
);

export default function GraphPage(): JSX.Element {
  const { learnerId, isLoading: learnerLoading, isAuthenticated } = useSessionLearner();
  const [graphData, setGraphData] = useState<LearnerGraph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [filters, setFilters] = useState<GraphFilterState>({
    selectedOutcome: null,
    showProvenOnly: false,
    showConcepts: true,
    showOutcomes: true,
    textFilter: "",
  });
  // Obsidian-style display options
  const [showLabels, setShowLabels] = useState(true);
  const [depthLimit, setDepthLimit] = useState(1); // Default to direct connections

  // Fetch graph data when learner is available
  useEffect(() => {
    if (learnerLoading) return;

    if (!learnerId) {
      setIsLoading(false);
      return;
    }

    const loadGraph = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await api.getLearnerGraph(learnerId);
        setGraphData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load graph");
      } finally {
        setIsLoading(false);
      }
    };

    loadGraph();
  }, [learnerId, learnerLoading]);

  // Transform API response to component format
  const nodes: KnowledgeNode[] = useMemo(() => {
    if (!graphData) return [];
    return graphData.nodes.map((node) => ({
      id: node.id,
      type: node.type as "outcome" | "concept",
      label: node.label,
      status: ((node.data?.status as string) || "identified") as KnowledgeNodeStatus,
      description: node.data?.description as string | undefined,
      proofCount: node.data?.proofCount as number | undefined,
    }));
  }, [graphData]);

  const edges: KnowledgeEdge[] = useMemo(() => {
    if (!graphData) return [];
    return graphData.edges.map((edge) => ({
      id: edge.id,
      from: edge.from_id,
      to: edge.to_id,
      type: edge.edge_type as "requires" | "relates_to" | "builds_on",
    }));
  }, [graphData]);

  // Extract outcomes for the filter dropdown
  const outcomes: OutcomeSnapshot[] = useMemo(() => {
    return nodes
      .filter((node) => node.type === "outcome")
      .map((node) => ({
        id: node.id,
        description: node.label,
        status: node.status as "active" | "achieved" | "paused" | "abandoned",
        concepts: [],
      }));
  }, [nodes]);

  const handleVoiceFilterUpdate = useCallback((update: GraphFilterUpdate) => {
    if (update.resetFilters) {
      setFilters({
        selectedOutcome: null,
        showProvenOnly: false,
        showConcepts: true,
        showOutcomes: true,
        textFilter: "",
      });
      return;
    }

    setFilters((prev) => ({
      ...prev,
      ...(update.showProvenOnly !== undefined && { showProvenOnly: update.showProvenOnly }),
      ...(update.showConcepts !== undefined && { showConcepts: update.showConcepts }),
      ...(update.showOutcomes !== undefined && { showOutcomes: update.showOutcomes }),
      ...(update.textFilter !== undefined && { textFilter: update.textFilter }),
    }));
  }, []);

  const filteredNodes = useMemo(() => {
    return nodes.filter((node) => {
      if (node.type === "outcome" && !filters.showOutcomes) return false;
      if (node.type === "concept" && !filters.showConcepts) return false;
      if (filters.showProvenOnly && node.status !== "proven" && node.status !== "achieved") {
        return false;
      }
      if (filters.selectedOutcome) {
        if (node.type === "outcome") return node.id === filters.selectedOutcome;
        return edges.some((e) => e.from === filters.selectedOutcome && e.to === node.id);
      }
      if (filters.textFilter) {
        const searchTerm = filters.textFilter.toLowerCase();
        return (
          node.label.toLowerCase().includes(searchTerm) ||
          node.description?.toLowerCase().includes(searchTerm)
        );
      }
      return true;
    });
  }, [filters, nodes, edges]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));
  }, [filteredNodes, edges]);

  const handleNodeClick = useCallback(
    (nodeId: string) => setSelectedNode(nodes.find((n) => n.id === nodeId) ?? null),
    [nodes]
  );

  const handleClosePanel = useCallback(() => setSelectedNode(null), []);

  const hasData = nodes.length > 0;

  // Handle loading state
  if (learnerLoading || isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 text-slate-400 mx-auto mb-2 animate-spin" />
          <div className="text-slate-500">Loading knowledge graph...</div>
        </div>
      </div>
    );
  }

  // Handle not authenticated
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Network className="h-16 w-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
            Please log in
          </h2>
          <p className="text-slate-500 dark:text-slate-400">
            Log in to view your knowledge graph.
          </p>
        </div>
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="h-16 w-16 text-red-300 dark:text-red-600 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-red-700 dark:text-red-300 mb-2">
            Error loading graph
          </h2>
          <p className="text-red-500 dark:text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            Knowledge Graph
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Visualize your learning journey
          </p>
        </div>
        <div className="flex gap-2">
          <button className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            <ZoomIn className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          </button>
          <button className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            <ZoomOut className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          </button>
          <button className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            <RefreshCw className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          </button>
        </div>
      </header>

      {hasData && (
        <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 space-y-3">
          <GraphFilters
            filters={filters}
            outcomes={outcomes}
            onFilterChange={setFilters}
            showLabels={showLabels}
            onShowLabelsChange={setShowLabels}
            depthLimit={depthLimit}
            onDepthLimitChange={setDepthLimit}
          />
          <VoiceCommandInput onFilterUpdate={handleVoiceFilterUpdate} />
        </div>
      )}

      <div className="flex-1 relative">
        {hasData ? (
          <>
            <KnowledgeGraph
              nodes={filteredNodes}
              edges={filteredEdges}
              onNodeClick={handleNodeClick}
              highlightedNode={selectedNode?.id}
              showLabels={showLabels}
              depthLimit={depthLimit}
            />
            <NodeDetailPanel node={selectedNode} onClose={handleClosePanel} />
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Network className="h-16 w-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h2 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
                No knowledge graph yet
              </h2>
              <p className="text-slate-500 dark:text-slate-400 max-w-md">
                Start learning through conversation, and your knowledge graph will
                grow as you prove understanding of new concepts.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
