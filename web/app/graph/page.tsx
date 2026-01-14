"use client";

import { useState, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { Network, ZoomIn, ZoomOut, RefreshCw } from "lucide-react";
import { NodeDetailPanel, GraphFilters } from "@/components/graph";
import type {
  KnowledgeNode,
  KnowledgeEdge,
  GraphFilterState,
  OutcomeSnapshot,
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

// Mock data for testing
const MOCK_NODES: KnowledgeNode[] = [
  {
    id: "outcome-1",
    type: "outcome",
    label: "Price freelance services confidently",
    status: "active",
    description: "Be able to confidently quote and negotiate pricing for freelance design work",
  },
  {
    id: "concept-1",
    type: "concept",
    label: "Value articulation",
    status: "proven",
    description: "Ability to clearly communicate the value you provide to clients",
    proofCount: 2,
  },
  {
    id: "concept-2",
    type: "concept",
    label: "Market positioning",
    status: "proven",
    description: "Understanding where you fit in the market relative to competitors",
    proofCount: 1,
  },
  {
    id: "concept-3",
    type: "concept",
    label: "Handling objections",
    status: "in_progress",
    description: "Techniques for responding when clients push back on pricing",
  },
  {
    id: "concept-4",
    type: "concept",
    label: "Scope definition",
    status: "identified",
    description: "Clearly defining project boundaries to prevent scope creep",
  },
  {
    id: "outcome-2",
    type: "outcome",
    label: "Run effective client meetings",
    status: "achieved",
    description: "Conduct productive client meetings that move projects forward",
  },
  {
    id: "concept-5",
    type: "concept",
    label: "Active listening",
    status: "proven",
    description: "Listening to understand client needs deeply",
    proofCount: 1,
  },
  {
    id: "concept-6",
    type: "concept",
    label: "Meeting structure",
    status: "proven",
    description: "How to organize and run an effective meeting",
    proofCount: 1,
  },
];

const MOCK_EDGES: KnowledgeEdge[] = [
  { id: "e1", from: "outcome-1", to: "concept-1", type: "requires" },
  { id: "e2", from: "outcome-1", to: "concept-2", type: "requires" },
  { id: "e3", from: "outcome-1", to: "concept-3", type: "requires" },
  { id: "e4", from: "outcome-1", to: "concept-4", type: "requires" },
  { id: "e5", from: "concept-1", to: "concept-3", type: "relates_to" },
  { id: "e6", from: "outcome-2", to: "concept-5", type: "requires" },
  { id: "e7", from: "outcome-2", to: "concept-6", type: "requires" },
  { id: "e8", from: "concept-5", to: "concept-1", type: "relates_to" },
  { id: "e9", from: "outcome-1", to: "outcome-2", type: "builds_on" },
];

const MOCK_OUTCOMES: OutcomeSnapshot[] = [
  {
    id: "outcome-1",
    description: "Price freelance services confidently",
    status: "active",
    concepts: [],
  },
  {
    id: "outcome-2",
    description: "Run effective client meetings",
    status: "achieved",
    concepts: [],
  },
];

export default function GraphPage(): JSX.Element {
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [filters, setFilters] = useState<GraphFilterState>({
    selectedOutcome: null,
    showProvenOnly: false,
    showConcepts: true,
    showOutcomes: true,
  });

  const filteredNodes = useMemo(() => {
    return MOCK_NODES.filter((node) => {
      if (node.type === "outcome" && !filters.showOutcomes) return false;
      if (node.type === "concept" && !filters.showConcepts) return false;
      if (filters.showProvenOnly && node.status !== "proven" && node.status !== "achieved") {
        return false;
      }
      if (filters.selectedOutcome) {
        if (node.type === "outcome") {
          return node.id === filters.selectedOutcome;
        }
        const relatedEdges = MOCK_EDGES.filter(
          (e) => e.from === filters.selectedOutcome && e.to === node.id
        );
        return relatedEdges.length > 0;
      }
      return true;
    });
  }, [filters]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return MOCK_EDGES.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));
  }, [filteredNodes]);

  const handleNodeClick = useCallback((nodeId: string) => {
    const node = MOCK_NODES.find((n) => n.id === nodeId);
    setSelectedNode(node || null);
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const hasData = MOCK_NODES.length > 0;

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
        <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
          <GraphFilters
            filters={filters}
            outcomes={MOCK_OUTCOMES}
            onFilterChange={setFilters}
          />
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
