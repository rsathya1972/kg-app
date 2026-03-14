"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  CheckCircle,
  ChevronRight,
  Circle,
  Loader2,
  RefreshCw,
  XCircle,
  Zap,
} from "lucide-react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  getAgentRun,
  listAgentRuns,
  listDocuments,
  streamAgentRun,
  triggerPipeline,
} from "@/lib/api";
import type {
  AgentDecision,
  AgentEvent,
  AgentRunDetail,
  AgentRunSummary,
  Document,
  StepResult,
  StepStatus,
} from "@/lib/types";

// ── Constants ──────────────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { key: "entity_extraction", label: "Entity Extraction", agent: "EntityExtractionAgent" },
  { key: "relationship_discovery", label: "Relationship Discovery", agent: "RelationshipDiscoveryAgent" },
  { key: "ontology_builder", label: "Ontology Builder", agent: "OntologyBuilderAgent" },
  { key: "graph_update", label: "Graph Update", agent: "GraphUpdateAgent" },
  { key: "vector_memory", label: "Vector Memory", agent: "VectorMemoryAgent" },
];

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-900 text-green-300 border-green-700",
  running:   "bg-blue-900 text-blue-300 border-blue-700",
  failed:    "bg-red-900 text-red-300 border-red-700",
  pending:   "bg-slate-800 text-slate-400 border-slate-700",
};

const NODE_STATUS_STYLE: Record<string, React.CSSProperties> = {
  completed: { background: "#166534", border: "1px solid #15803d", color: "#bbf7d0" },
  running:   { background: "#1e3a5f", border: "1px solid #3b82f6", color: "#93c5fd" },
  failed:    { background: "#7f1d1d", border: "1px solid #dc2626", color: "#fca5a5" },
  pending:   { background: "#1e293b", border: "1px solid #475569", color: "#94a3b8" },
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

function formatDuration(ms: number | null): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function stepStatus(steps: StepResult[], key: string): StepStatus {
  return steps.find((s) => s.step_name === key)?.status ?? "pending";
}

// ── Step icon ──────────────────────────────────────────────────────────────────

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "completed") return <CheckCircle className="w-5 h-5 text-green-400" />;
  if (status === "running")   return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
  if (status === "failed")    return <XCircle className="w-5 h-5 text-red-400" />;
  return <Circle className="w-5 h-5 text-slate-600" />;
}

// ── React Flow DAG ─────────────────────────────────────────────────────────────

function buildDagElements(steps: StepResult[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = PIPELINE_STEPS.map((step, i) => {
    const status = stepStatus(steps, step.key);
    return {
      id: step.key,
      data: { label: step.label },
      position: { x: i * 210, y: 120 },
      style: {
        ...NODE_STATUS_STYLE[status],
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 12,
        fontWeight: 600,
        minWidth: 160,
        textAlign: "center" as const,
        boxShadow: status === "running" ? "0 0 12px rgba(59,130,246,0.5)" : undefined,
      },
    };
  });

  const edges: Edge[] = PIPELINE_STEPS.slice(0, -1).map((step, i) => ({
    id: `e-${i}`,
    source: step.key,
    target: PIPELINE_STEPS[i + 1].key,
    style: { stroke: "#475569", strokeWidth: 1.5 },
    animated: stepStatus(steps, step.key) === "running",
  }));

  return { nodes, edges };
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [domainHint, setDomainHint] = useState("");
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState<AgentRunDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"timeline" | "graph" | "decisions">("timeline");
  const [triggering, setTriggering] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // SSE cleanup ref
  const sseCleanupRef = useRef<(() => void) | null>(null);

  // Load documents on mount
  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  // Load runs on mount and periodically
  const loadRuns = useCallback(async () => {
    setLoadingRuns(true);
    try {
      const data = await listAgentRuns({ limit: 30 });
      setRuns(data.runs);
    } catch {
      // silent
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
    const interval = setInterval(loadRuns, 5000);
    return () => clearInterval(interval);
  }, [loadRuns]);

  // Open SSE stream when a run is selected and still active
  useEffect(() => {
    if (!selectedRun) return;
    if (!["pending", "running"].includes(selectedRun.status)) return;

    // Close any existing stream
    sseCleanupRef.current?.();

    const cleanup = streamAgentRun(selectedRun.id, async (event: AgentEvent) => {
      if (event.type === "ping") return;

      // Reload full run detail on each event
      try {
        const updated = await getAgentRun(selectedRun.id);
        setSelectedRun(updated);

        // Also update summary in run list
        setRuns((prev) =>
          prev.map((r) =>
            r.id === updated.id
              ? {
                  ...r,
                  status: updated.status,
                  current_step: updated.current_step,
                  completed_steps_count: updated.completed_steps_count,
                }
              : r
          )
        );
      } catch {
        // ignore
      }

      if (["run_complete", "run_failed", "done"].includes(event.type)) {
        cleanup();
        sseCleanupRef.current = null;
        loadRuns();
      }
    });

    sseCleanupRef.current = cleanup;
    return () => {
      cleanup();
      sseCleanupRef.current = null;
    };
  }, [selectedRun?.id, selectedRun?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectRun = async (run: AgentRunSummary) => {
    try {
      const detail = await getAgentRun(run.id);
      setSelectedRun(detail);
      setActiveTab("timeline");
    } catch {
      setError("Failed to load run details");
    }
  };

  const handleTrigger = async () => {
    if (!selectedDocId) return;
    setTriggering(true);
    setError(null);
    try {
      const { run_id } = await triggerPipeline(selectedDocId, {
        domain_hint: domainHint || undefined,
      });
      await loadRuns();
      // Auto-select the new run
      const detail = await getAgentRun(run_id);
      setSelectedRun(detail);
      setActiveTab("timeline");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to trigger pipeline");
    } finally {
      setTriggering(false);
    }
  };

  // DAG elements derived from selected run's steps
  const { nodes: dagNodes, edges: dagEdges } = useMemo(
    () => buildDagElements(selectedRun?.steps ?? []),
    [selectedRun?.steps]
  );

  return (
    <div className="flex flex-col gap-4 max-w-7xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <Bot className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Agent Monitor</h1>
          <p className="text-slate-500 text-sm">
            Orchestrate the AI pipeline and observe agent decisions in real-time
          </p>
        </div>
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-3 flex-wrap">
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

        <input
          type="text"
          value={domainHint}
          onChange={(e) => setDomainHint(e.target.value)}
          placeholder="Domain hint (optional, e.g. &quot;saas&quot;)"
          className="input w-52"
        />

        <button
          onClick={handleTrigger}
          disabled={!selectedDocId || triggering}
          className="btn-primary flex items-center gap-2"
        >
          {triggering ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          {triggering ? "Triggering…" : "Run Pipeline"}
        </button>

        <button
          onClick={loadRuns}
          disabled={loadingRuns}
          className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-400 hover:text-slate-200 border border-slate-700 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loadingRuns ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Two-column layout */}
      <div className="flex gap-4 items-start">
        {/* Run list sidebar */}
        <div className="w-64 shrink-0 flex flex-col gap-2">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider px-1">
            Recent Runs ({runs.length})
          </p>
          {runs.length === 0 ? (
            <div className="card py-8 flex flex-col items-center gap-2 border-dashed">
              <Bot className="w-8 h-8 text-slate-700" />
              <p className="text-slate-600 text-xs text-center">No runs yet</p>
            </div>
          ) : (
            runs.map((run) => (
              <button
                key={run.id}
                onClick={() => handleSelectRun(run)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  selectedRun?.id === run.id
                    ? "bg-brand-900/50 border-brand-700"
                    : "bg-slate-900 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-slate-200 truncate max-w-[120px]">
                    {run.document_name ?? "Unknown doc"}
                  </span>
                  <span
                    className={`badge text-[10px] ${STATUS_COLORS[run.status] ?? STATUS_COLORS.pending}`}
                  >
                    {run.status}
                  </span>
                </div>
                <div className="text-[10px] text-slate-500">
                  {relativeTime(run.started_at)}
                  {run.status === "running" && run.current_step && (
                    <span className="ml-1 text-blue-400">
                      · {run.current_step.replace("_", " ")}
                    </span>
                  )}
                </div>
                {/* Mini progress bar */}
                <div className="mt-1.5 h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      run.status === "failed" ? "bg-red-500" :
                      run.status === "completed" ? "bg-green-500" : "bg-blue-500"
                    }`}
                    style={{
                      width: `${Math.round((run.completed_steps_count / run.steps_count) * 100)}%`,
                    }}
                  />
                </div>
              </button>
            ))
          )}
        </div>

        {/* Run detail */}
        <div className="flex-1 min-w-0">
          {!selectedRun ? (
            <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
              <Bot className="w-10 h-10 text-slate-600" />
              <p className="text-slate-500 text-sm">
                Select a run from the sidebar, or trigger a new pipeline
              </p>
            </div>
          ) : (
            <div className="card p-0 overflow-hidden">
              {/* Run header */}
              <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-100 font-semibold">
                      {selectedRun.document_name ?? "Unknown document"}
                    </span>
                    <span
                      className={`badge ${STATUS_COLORS[selectedRun.status] ?? STATUS_COLORS.pending}`}
                    >
                      {selectedRun.status}
                    </span>
                    {selectedRun.status === "running" && (
                      <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin" />
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {selectedRun.completed_steps_count}/{selectedRun.steps_count} steps ·{" "}
                    {relativeTime(selectedRun.started_at)}
                    {selectedRun.completed_at && (
                      <> · finished {relativeTime(selectedRun.completed_at)}</>
                    )}
                  </p>
                </div>
                <code className="text-[10px] text-slate-600 font-mono">
                  {selectedRun.id.slice(0, 8)}
                </code>
              </div>

              {/* Tab bar */}
              <div className="flex gap-0 border-b border-slate-800 px-5">
                {(["timeline", "graph", "decisions"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2.5 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
                      activeTab === tab
                        ? "border-brand-500 text-brand-400"
                        : "border-transparent text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {tab === "graph" ? "Task Graph" : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="p-5">
                {/* ── Timeline tab ── */}
                {activeTab === "timeline" && (
                  <div className="flex flex-col gap-3">
                    {PIPELINE_STEPS.map((stepDef, i) => {
                      const step = selectedRun.steps.find(
                        (s) => s.step_name === stepDef.key
                      );
                      const status: StepStatus = step?.status ?? "pending";

                      return (
                        <div key={stepDef.key} className="flex gap-3">
                          {/* Connector line */}
                          <div className="flex flex-col items-center">
                            <StepIcon status={status} />
                            {i < PIPELINE_STEPS.length - 1 && (
                              <div className="w-px flex-1 bg-slate-800 mt-1" />
                            )}
                          </div>

                          {/* Step card */}
                          <div
                            className={`flex-1 mb-3 p-3 rounded-lg border ${
                              status === "running"
                                ? "border-blue-700 bg-blue-900/20"
                                : status === "completed"
                                ? "border-green-800 bg-green-900/10"
                                : status === "failed"
                                ? "border-red-800 bg-red-900/10"
                                : "border-slate-800 bg-slate-800/30"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium text-slate-200">
                                {stepDef.label}
                              </span>
                              <div className="flex items-center gap-2">
                                {step?.duration_ms != null && (
                                  <span className="text-xs text-slate-500">
                                    {formatDuration(step.duration_ms)}
                                  </span>
                                )}
                                <span
                                  className={`badge text-[10px] ${STATUS_COLORS[status]}`}
                                >
                                  {status}
                                </span>
                              </div>
                            </div>
                            {step?.output_summary && (
                              <p className="text-xs text-slate-400 mt-1">
                                {step.output_summary}
                              </p>
                            )}
                            {step?.error && (
                              <p className="text-xs text-red-400 mt-1 font-mono">
                                {step.error}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* ── Task Graph tab ── */}
                {activeTab === "graph" && (
                  <div
                    className="rounded-xl overflow-hidden border border-slate-700 bg-slate-950"
                    style={{ height: 300 }}
                  >
                    <ReactFlowProvider>
                      <ReactFlow
                        nodes={dagNodes}
                        edges={dagEdges}
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable={false}
                        fitView
                        fitViewOptions={{ padding: 0.3 }}
                        proOptions={{ hideAttribution: true }}
                      >
                        <Background color="#334155" gap={20} />
                      </ReactFlow>
                    </ReactFlowProvider>
                  </div>
                )}

                {/* ── Decisions tab ── */}
                {activeTab === "decisions" && (
                  <div className="flex flex-col gap-2">
                    {selectedRun.decisions.length === 0 ? (
                      <p className="text-slate-500 text-sm text-center py-8">
                        No decisions recorded yet
                      </p>
                    ) : (
                      selectedRun.decisions.map((d: AgentDecision, i: number) => (
                        <div
                          key={i}
                          className="flex gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-800"
                        >
                          <ChevronRight className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-semibold text-brand-400">
                                {d.agent}
                              </span>
                              <span className="text-xs text-slate-600">
                                {new Date(d.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            <p className="text-sm text-slate-300 font-mono whitespace-pre-wrap break-all">
                              {d.message}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
