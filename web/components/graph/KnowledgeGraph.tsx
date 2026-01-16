"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Network, Options } from "vis-network";
import { DataSet } from "vis-data";
import type { KnowledgeNode, KnowledgeEdge } from "@/types";

export interface KnowledgeGraphProps {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  highlightedNode?: string | null;
  /** Show labels on all nodes (false = show only on hover) */
  showLabels?: boolean;
  /** Connection depth filter (0 = all, 1 = direct, 2 = 2nd degree) */
  depthLimit?: number;
}

// Obsidian-style color scheme - subtle, monochromatic
const OBSIDIAN_COLORS = {
  // Node colors by type (not status)
  outcome: {
    default: { background: "#8b5cf6", border: "#7c3aed" }, // Purple for goals
    hover: { background: "#a78bfa", border: "#8b5cf6" },
  },
  concept: {
    default: { background: "#64748b", border: "#475569" }, // Slate for concepts
    hover: { background: "#94a3b8", border: "#64748b" },
  },
  // Status indicators (subtle accents)
  status: {
    proven: "#22c55e",
    achieved: "#22c55e",
    in_progress: "#f59e0b",
    active: "#8b5cf6",
    identified: "#64748b",
  },
  // Edge color (single subtle color)
  edge: {
    default: "#475569",
    hover: "#94a3b8",
    highlight: "#8b5cf6",
  },
  // Background
  background: {
    light: "#f8fafc",
    dark: "#0f172a",
  },
};

function transformNodes(
  nodes: KnowledgeNode[],
  showLabels: boolean,
  connectedNodeIds?: Set<string>,
  hoveredNodeId?: string | null
) {
  return nodes.map((node) => {
    const isOutcome = node.type === "outcome";
    const colors = isOutcome ? OBSIDIAN_COLORS.outcome : OBSIDIAN_COLORS.concept;
    const statusColor = OBSIDIAN_COLORS.status[node.status as keyof typeof OBSIDIAN_COLORS.status] || OBSIDIAN_COLORS.status.identified;

    // Highlight connected nodes when hovering
    const isConnected = connectedNodeIds?.has(node.id) || node.id === hoveredNodeId;
    const isHovered = node.id === hoveredNodeId;

    // Dim non-connected nodes when something is hovered
    const isDimmed = hoveredNodeId && !isConnected;

    return {
      id: node.id,
      label: showLabels || isHovered ? node.label : "",
      title: `${node.label}${node.description ? `\n${node.description}` : ""}${node.proofCount ? `\n✓ ${node.proofCount} proof${node.proofCount > 1 ? "s" : ""}` : ""}`,
      color: {
        background: isDimmed ? "#334155" : colors.default.background,
        border: isConnected ? statusColor : colors.default.border,
        highlight: {
          background: colors.hover.background,
          border: statusColor,
        },
        hover: {
          background: colors.hover.background,
          border: statusColor,
        },
      },
      // Obsidian uses dots - smaller, more uniform
      shape: "dot",
      size: isOutcome ? 16 : 12,
      font: {
        color: isDimmed ? "#64748b" : "#e2e8f0",
        size: isOutcome ? 12 : 10,
        face: "Inter, system-ui, sans-serif",
        strokeWidth: 2,
        strokeColor: "#0f172a",
      },
      borderWidth: isConnected ? 3 : 2,
      borderWidthSelected: 4,
      opacity: isDimmed ? 0.3 : 1,
    };
  });
}

function transformEdges(
  edges: KnowledgeEdge[],
  connectedEdgeIds?: Set<string>,
  hoveredNodeId?: string | null
) {
  return edges.map((edge) => {
    const isConnected = connectedEdgeIds?.has(edge.id);
    const isDimmed = hoveredNodeId && !isConnected;

    return {
      id: edge.id,
      from: edge.from,
      to: edge.to,
      color: {
        color: isDimmed ? "#1e293b" : OBSIDIAN_COLORS.edge.default,
        highlight: OBSIDIAN_COLORS.edge.highlight,
        hover: OBSIDIAN_COLORS.edge.hover,
        opacity: isDimmed ? 0.2 : 0.8,
      },
      // Subtle arrows only for directional relationships
      arrows: edge.type === "requires" || edge.type === "builds_on"
        ? { to: { enabled: true, scaleFactor: 0.5 } }
        : undefined,
      dashes: edge.type === "relates_to" ? [4, 4] : false,
      width: isConnected ? 2 : 1,
      smooth: {
        enabled: true,
        type: "continuous" as const,
        roundness: 0.3,
      },
    };
  });
}

// Obsidian-style physics - tighter clustering, less bouncy
const networkOptions: Options = {
  physics: {
    enabled: true,
    solver: "forceAtlas2Based",
    forceAtlas2Based: {
      gravitationalConstant: -80,
      centralGravity: 0.005,
      springLength: 100,
      springConstant: 0.05,
      damping: 0.7,
      avoidOverlap: 0.5,
    },
    stabilization: {
      enabled: true,
      iterations: 300,
      updateInterval: 20,
    },
    maxVelocity: 30,
    minVelocity: 0.1,
  },
  interaction: {
    hover: true,
    tooltipDelay: 100,
    zoomView: true,
    dragView: true,
    navigationButtons: false,
    hideEdgesOnDrag: true,
    hideEdgesOnZoom: true,
  },
  layout: {
    improvedLayout: true,
    randomSeed: 42, // Consistent layout
  },
};

export function KnowledgeGraph({
  nodes,
  edges,
  onNodeClick,
  onNodeHover,
  highlightedNode,
  showLabels = true,
  depthLimit = 0,
}: KnowledgeGraphProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const nodesDataSetRef = useRef<DataSet<ReturnType<typeof transformNodes>[0]> | null>(null);
  const edgesDataSetRef = useRef<DataSet<ReturnType<typeof transformEdges>[0]> | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Build adjacency map for bidirectional highlighting
  const adjacencyMap = useRef<Map<string, Set<string>>>(new Map());
  const edgeMap = useRef<Map<string, Set<string>>>(new Map());

  useEffect(() => {
    // Build adjacency map
    const adj = new Map<string, Set<string>>();
    const edgeM = new Map<string, Set<string>>();

    edges.forEach((edge) => {
      if (!adj.has(edge.from)) adj.set(edge.from, new Set());
      if (!adj.has(edge.to)) adj.set(edge.to, new Set());
      adj.get(edge.from)!.add(edge.to);
      adj.get(edge.to)!.add(edge.from);

      if (!edgeM.has(edge.from)) edgeM.set(edge.from, new Set());
      if (!edgeM.has(edge.to)) edgeM.set(edge.to, new Set());
      edgeM.get(edge.from)!.add(edge.id);
      edgeM.get(edge.to)!.add(edge.id);
    });

    adjacencyMap.current = adj;
    edgeMap.current = edgeM;
  }, [edges]);

  // Get connected nodes for highlighting (respecting depth limit)
  const getConnectedNodes = useCallback((nodeId: string, depth: number = 1): Set<string> => {
    const connected = new Set<string>();
    const visited = new Set<string>();
    const queue: [string, number][] = [[nodeId, 0]];

    while (queue.length > 0) {
      const [current, currentDepth] = queue.shift()!;
      if (visited.has(current)) continue;
      visited.add(current);
      connected.add(current);

      if (currentDepth < depth) {
        const neighbors = adjacencyMap.current.get(current) || new Set();
        neighbors.forEach((neighbor) => {
          if (!visited.has(neighbor)) {
            queue.push([neighbor, currentDepth + 1]);
          }
        });
      }
    }

    return connected;
  }, []);

  const getConnectedEdges = useCallback((nodeIds: Set<string>): Set<string> => {
    const connectedEdges = new Set<string>();
    nodeIds.forEach((nodeId) => {
      const nodeEdges = edgeMap.current.get(nodeId) || new Set();
      nodeEdges.forEach((edgeId) => {
        const edge = edges.find((e) => e.id === edgeId);
        if (edge && nodeIds.has(edge.from) && nodeIds.has(edge.to)) {
          connectedEdges.add(edgeId);
        }
      });
    });
    return connectedEdges;
  }, [edges]);

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
      setHoveredNode(params.node);
      if (onNodeHover) {
        onNodeHover(params.node);
      }
    },
    [onNodeHover]
  );

  // Update visualization when hover changes
  useEffect(() => {
    if (!nodesDataSetRef.current || !edgesDataSetRef.current) return;

    const connectedNodes = hoveredNode
      ? getConnectedNodes(hoveredNode, depthLimit || 1)
      : undefined;
    const connectedEdges = connectedNodes
      ? getConnectedEdges(connectedNodes)
      : undefined;

    const transformedNodes = transformNodes(nodes, showLabels, connectedNodes, hoveredNode);
    const transformedEdges = transformEdges(edges, connectedEdges, hoveredNode);

    nodesDataSetRef.current.update(transformedNodes);
    edgesDataSetRef.current.update(transformedEdges);
  }, [hoveredNode, nodes, edges, showLabels, depthLimit, getConnectedNodes, getConnectedEdges]);

  useEffect(() => {
    if (!containerRef.current) return;

    const transformedNodes = transformNodes(nodes, showLabels);
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
    network.on("blurNode", () => handleNodeHover({ node: null }));

    networkRef.current = network;

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges, handleNodeClick, handleNodeHover, showLabels]);

  useEffect(() => {
    if (networkRef.current && highlightedNode) {
      networkRef.current.selectNodes([highlightedNode]);
      networkRef.current.focus(highlightedNode, {
        scale: 1.5,
        animation: {
          duration: 400,
          easingFunction: "easeOutQuad",
        },
      });
    }
  }, [highlightedNode]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-slate-50 dark:bg-slate-950 rounded-lg transition-colors"
      style={{ minHeight: "400px" }}
    />
  );
}
