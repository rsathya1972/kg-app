"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Network, RefreshCw, Zap } from "lucide-react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  buildGraph,
  getDocumentGraph,
  listDocuments,
} from "@/lib/api";
import type { Document, GraphNode, GraphResponse, GraphWriteResponse } from "@/lib/types";

// ── Colour palette per entity label ───────────────────────────────────────────

const NODE_COLORS: Record<string, string> = {
  Company: "#2563eb",
  Organization: "#2563eb",
  Person: "#16a34a",
  Technology: "#7c3aed",
  Product: "#ea580c",
  Location: "#e11d48",
  Event: "#0891b2",
  Concept: "#d97706",
  Service: "#9333ea",
};

function nodeColor(labels: string[]): string {
  for (const lbl of labels) {
    if (NODE_COLORS[lbl]) return NODE_COLORS[lbl];
  }
  return "#475569"; // slate-600 default
}

// ── Layout helpers ─────────────────────────────────────────────────────────────

function circularLayout(
  index: number,
  total: number,
  cx = 600,
  cy = 350,
  R = 280
): { x: number; y: number } {
  if (total === 1) return { x: cx, y: cy };
  const angle = (2 * Math.PI * index) / total - Math.PI / 2;
  return { x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle) };
}

// ── Convert API response to React Flow elements ────────────────────────────────

function toFlowElements(
  data: GraphResponse,
  activeLabels: Set<string>
): { nodes: Node[]; edges: Edge[] } {
  const visibleIds = new Set(
    data.nodes
      .filter((n) => n.labels.some((l) => activeLabels.has(l)) || n.labels.length === 0)
      .map((n) => n.id)
  );

  const nodes: Node[] = data.nodes
    .filter((n) => visibleIds.has(n.id))
    .map((n, i) => ({
      id: n.id,
      data: { label: n.properties.name ?? n.id, raw: n },
      position: circularLayout(i, visibleIds.size),
      style: {
        background: nodeColor(n.labels),
        color: "#fff",
        border: "none",
        borderRadius: 8,
        padding: "6px 10px",
        fontSize: 12,
        fontWeight: 600,
        minWidth: 80,
        textAlign: "center" as const,
        boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
      },
    }));

  const edges: Edge[] = data.edges
    .filter((e) => visibleIds.has(e.source_id) && visibleIds.has(e.target_id))
    .map((e) => ({
      id: e.id,
      source: e.source_id,
      target: e.target_id,
      label: e.type,
      labelStyle: { fontSize: 10, fill: "#94a3b8" },
      labelBgStyle: { fill: "#1e293b", fillOpacity: 0.8 },
      style: { stroke: "#475569", strokeWidth: 1.5 },
      animated: false,
    }));

  return { nodes, edges };
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function GraphPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [buildResult, setBuildResult] = useState<GraphWriteResponse | null>(null);
  const [activeLabels, setActiveLabels] = useState<Set<string>>(new Set());
  const [building, setBuilding] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  // Load document list on mount
  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  // Load graph when document selected
  useEffect(() => {
    if (!selectedDocId) {
      setGraphData(null);
      setBuildResult(null);
      setSelectedNode(null);
      return;
    }
    setLoading(true);
    setError(null);
    getDocumentGraph(selectedDocId)
      .then((data) => {
        setGraphData(data);
        const labels = new Set(data.nodes.flatMap((n) => n.labels));
        setActiveLabels(labels);
      })
      .catch((e: Error) => {
        if (e.message.includes("503")) {
          setError("Neo4j is not running. Start Neo4j and rebuild the graph.");
        } else {
          // Empty graph is fine — just no data yet
          setGraphData({ nodes: [], edges: [], node_count: 0, edge_count: 0 });
          setActiveLabels(new Set());
        }
      })
      .finally(() => setLoading(false));
  }, [selectedDocId]);

  // Derived: all unique labels in graph
  const allLabels = useMemo(
    () => Array.from(new Set(graphData?.nodes.flatMap((n) => n.labels) ?? [])).sort(),
    [graphData]
  );

  const { nodes: flowNodes, edges: flowEdges } = useMemo(
    () =>
      graphData
        ? toFlowElements(graphData, activeLabels)
        : { nodes: [], edges: [] },
    [graphData, activeLabels]
  );

  const handleBuild = async () => {
    if (!selectedDocId) return;
    setBuilding(true);
    setError(null);
    try {
      const result = await buildGraph(selectedDocId);
      setBuildResult(result);
      showToast(
        `Graph built: ${result.nodes_created} nodes created, ${result.edges_created} edges created`
      );
      // Reload graph
      const data = await getDocumentGraph(selectedDocId);
      setGraphData(data);
      setActiveLabels(new Set(data.nodes.flatMap((n) => n.labels)));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("503")) {
        setError("Neo4j is not running. Start it with: docker compose up neo4j");
      } else if (msg.includes("422")) {
        setError("No entities found for this document. Extract entities first.");
      } else {
        setError(msg);
      }
    } finally {
      setBuilding(false);
    }
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  };

  const onNodeClick: NodeMouseHandler = useCallback(
    (_evt, node) => {
      const raw = (node.data as { raw: GraphNode }).raw;
      setSelectedNode(raw);
    },
    []
  );

  const toggleLabel = (label: string) => {
    setActiveLabels((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

  // Parse attributes JSON for display
  const parsedAttributes = useMemo(() => {
    if (!selectedNode?.properties.attributes) return null;
    try {
      return JSON.parse(selectedNode.properties.attributes) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [selectedNode]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <Network className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Graph Viewer</h1>
          <p className="text-slate-500 text-sm">Explore the Neo4j knowledge graph interactively</p>
        </div>
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <select
          className="input w-64"
          value={selectedDocId}
          onChange={(e) => setSelectedDocId(e.target.value)}
        >
          <option value="">Select a document…</option>
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.filename ?? doc.id}
            </option>
          ))}
        </select>

        <button
          onClick={handleBuild}
          disabled={!selectedDocId || building}
          className="btn-primary flex items-center gap-2"
        >
          {building ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          {building ? "Building…" : "Build Graph"}
        </button>

        {graphData && graphData.node_count > 0 && (
          <div className="flex items-center gap-2 ml-2">
            <span className="badge bg-blue-900 text-blue-300 border border-blue-700">
              {graphData.node_count} nodes
            </span>
            <span className="badge bg-slate-800 text-slate-300 border border-slate-600">
              {graphData.edge_count} edges
            </span>
          </div>
        )}
      </div>

      {/* Filter pills */}
      {allLabels.length > 0 && (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className="text-xs text-slate-500 mr-1">Filter:</span>
          {allLabels.map((lbl) => (
            <button
              key={lbl}
              onClick={() => toggleLabel(lbl)}
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium border transition-all ${
                activeLabels.has(lbl)
                  ? "border-transparent text-white"
                  : "border-slate-600 bg-transparent text-slate-500"
              }`}
              style={
                activeLabels.has(lbl)
                  ? { background: nodeColor([lbl]) }
                  : undefined
              }
            >
              {lbl}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-3 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Main area: graph + detail panel */}
      <div className="flex gap-4 flex-1 min-h-0" style={{ height: "calc(100vh - 280px)" }}>
        {/* Graph canvas */}
        <div className="flex-1 rounded-xl overflow-hidden border border-slate-700 bg-slate-950">
          {!selectedDocId ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <Network className="w-12 h-12 text-slate-700" />
              <p className="text-slate-500">Select a document to view its knowledge graph</p>
            </div>
          ) : loading ? (
            <div className="flex items-center justify-center h-full">
              <RefreshCw className="w-6 h-6 text-slate-500 animate-spin" />
            </div>
          ) : flowNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <Network className="w-12 h-12 text-slate-700" />
              <p className="text-slate-400 font-medium">No graph data yet</p>
              <p className="text-slate-500 text-sm">
                Click <strong className="text-slate-300">Build Graph</strong> to populate Neo4j
              </p>
            </div>
          ) : (
            <ReactFlowProvider>
              <ReactFlow
                nodes={flowNodes}
                edges={flowEdges}
                onNodeClick={onNodeClick}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.2}
                maxZoom={2}
              >
                <Background color="#334155" gap={20} />
                <Controls />
                <MiniMap
                  nodeColor={(n) => {
                    const raw = (n.data as { raw?: GraphNode }).raw;
                    return raw ? nodeColor(raw.labels) : "#475569";
                  }}
                  style={{ background: "#0f172a" }}
                />
              </ReactFlow>
            </ReactFlowProvider>
          )}
        </div>

        {/* Detail panel */}
        {selectedNode && (
          <div className="w-72 card flex-shrink-0 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-slate-100 truncate">
                {selectedNode.properties.name ?? selectedNode.id}
              </h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-500 hover:text-slate-300 text-xs ml-2"
              >
                ✕
              </button>
            </div>

            <div className="flex flex-wrap gap-1 mb-3">
              {selectedNode.labels.map((lbl) => (
                <span
                  key={lbl}
                  className="px-2 py-0.5 rounded-full text-xs font-medium text-white"
                  style={{ background: nodeColor([lbl]) }}
                >
                  {lbl}
                </span>
              ))}
            </div>

            {selectedNode.properties.confidence != null && (
              <div className="mb-3">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Confidence</span>
                  <span>{(selectedNode.properties.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 rounded-full"
                    style={{ width: `${selectedNode.properties.confidence * 100}%` }}
                  />
                </div>
              </div>
            )}

            {parsedAttributes && Object.keys(parsedAttributes).length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wide">
                  Attributes
                </p>
                <div className="space-y-1">
                  {Object.entries(parsedAttributes).map(([k, v]) => (
                    <div key={k} className="flex gap-2 text-xs">
                      <span className="text-slate-500 min-w-0 shrink-0">{k}:</span>
                      <span className="text-slate-300 break-all">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-3 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-600 font-mono break-all">{selectedNode.id}</p>
            </div>
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-green-800 text-green-100 px-4 py-3 rounded-lg shadow-xl text-sm border border-green-600 z-50">
          {toast}
        </div>
      )}
    </div>
  );
}
