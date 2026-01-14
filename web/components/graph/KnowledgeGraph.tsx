"use client";

import { useEffect, useRef, useCallback } from "react";
import { Network, Options } from "vis-network";
import { DataSet } from "vis-data";
import type { KnowledgeNode, KnowledgeEdge } from "@/types";

export interface KnowledgeGraphProps {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  highlightedNode?: string | null;
}

const NODE_COLORS: Record<string, { background: string; border: string }> = {
  proven: { background: "#22c55e", border: "#16a34a" },
  in_progress: { background: "#eab308", border: "#ca8a04" },
  identified: { background: "#94a3b8", border: "#64748b" },
  active: { background: "#6366f1", border: "#4f46e5" },
  achieved: { background: "#22c55e", border: "#16a34a" },
};

const EDGE_COLORS: Record<string, string> = {
  requires: "#94a3b8",
  relates_to: "#6366f1",
  builds_on: "#22c55e",
};

function transformNodes(nodes: KnowledgeNode[]) {
  return nodes.map((node) => {
    const colors = NODE_COLORS[node.status] || NODE_COLORS.identified;
    const isOutcome = node.type === "outcome";

    return {
      id: node.id,
      label: node.label,
      title: node.description || node.label,
      color: {
        background: colors.background,
        border: colors.border,
        highlight: {
          background: colors.background,
          border: "#000",
        },
        hover: {
          background: colors.background,
          border: "#000",
        },
      },
      shape: isOutcome ? "box" : "ellipse",
      size: isOutcome ? 30 : 20,
      font: {
        color: "#fff",
        size: isOutcome ? 14 : 12,
        face: "system-ui, sans-serif",
      },
      borderWidth: 2,
      borderWidthSelected: 3,
    };
  });
}

function transformEdges(edges: KnowledgeEdge[]) {
  return edges.map((edge) => ({
    id: edge.id,
    from: edge.from,
    to: edge.to,
    color: {
      color: EDGE_COLORS[edge.type] || "#94a3b8",
      highlight: "#000",
      hover: "#000",
    },
    arrows: edge.type === "requires" || edge.type === "builds_on" ? "to" : undefined,
    dashes: edge.type === "relates_to",
    width: 2,
    smooth: {
      enabled: true,
      type: "continuous" as const,
      roundness: 0.5,
    },
  }));
}

const networkOptions: Options = {
  physics: {
    enabled: true,
    solver: "forceAtlas2Based",
    forceAtlas2Based: {
      gravitationalConstant: -50,
      centralGravity: 0.01,
      springLength: 150,
      springConstant: 0.08,
      damping: 0.4,
    },
    stabilization: {
      enabled: true,
      iterations: 200,
      updateInterval: 25,
    },
  },
  interaction: {
    hover: true,
    tooltipDelay: 200,
    zoomView: true,
    dragView: true,
    navigationButtons: false,
  },
  layout: {
    improvedLayout: true,
  },
};

export function KnowledgeGraph({
  nodes,
  edges,
  onNodeClick,
  onNodeHover,
  highlightedNode,
}: KnowledgeGraphProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const nodesDataSetRef = useRef<DataSet<ReturnType<typeof transformNodes>[0]> | null>(null);
  const edgesDataSetRef = useRef<DataSet<ReturnType<typeof transformEdges>[0]> | null>(null);

  const handleNodeClick = useCallback(
    (params: { nodes: string[] }) => {
      if (params.nodes.length > 0 && onNodeClick) {
        onNodeClick(params.nodes[0]);
      }
    },
    [onNodeClick]
  );

  const handleNodeHover = useCallback(
    (params: { node: string | null }) => {
      if (onNodeHover) {
        onNodeHover(params.node);
      }
    },
    [onNodeHover]
  );

  useEffect(() => {
    if (!containerRef.current) return;

    const transformedNodes = transformNodes(nodes);
    const transformedEdges = transformEdges(edges);

    nodesDataSetRef.current = new DataSet(transformedNodes);
    edgesDataSetRef.current = new DataSet(transformedEdges);

    const network = new Network(
      containerRef.current,
      {
        nodes: nodesDataSetRef.current,
        edges: edgesDataSetRef.current,
      },
      networkOptions
    );

    network.on("click", handleNodeClick);
    network.on("hoverNode", handleNodeHover);
    network.on("blurNode", () => onNodeHover?.(null));

    networkRef.current = network;

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges, handleNodeClick, handleNodeHover, onNodeHover]);

  useEffect(() => {
    if (networkRef.current && highlightedNode) {
      networkRef.current.selectNodes([highlightedNode]);
      networkRef.current.focus(highlightedNode, {
        scale: 1.2,
        animation: {
          duration: 500,
          easingFunction: "easeInOutQuad",
        },
      });
    }
  }, [highlightedNode]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-slate-50 dark:bg-slate-900 rounded-lg"
      style={{ minHeight: "400px" }}
    />
  );
}
