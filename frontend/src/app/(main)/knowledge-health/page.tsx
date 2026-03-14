"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  GitBranch,
  Info,
  Loader2,
  RefreshCw,
  Sparkles,
  Zap,
} from "lucide-react";
import {
  triggerAnalysis,
  getMetrics,
  listIssues,
  listProposals,
  applyProposal,
  dismissProposal,
  listEntities,
} from "@/lib/api";
import type {
  AnalysisResult,
  EvaluationMetrics,
  KnowledgeIssue,
  OntologyProposal,
  Entity,
} from "@/lib/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

type Tab = "metrics" | "issues" | "proposals" | "heatmap";

function pct(v: number): string {
  return (v * 100).toFixed(1) + "%";
}

function accuracyColor(v: number): string {
  if (v >= 0.8) return "text-green-400";
  if (v >= 0.6) return "text-amber-400";
  return "text-red-400";
}

function barColor(v: number): string {
  if (v >= 0.8) return "bg-green-500";
  if (v >= 0.6) return "bg-amber-500";
  return "bg-red-500";
}

function severityIcon(severity: string) {
  if (severity === "error")
    return <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />;
  if (severity === "warning")
    return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />;
  return <Info className="w-4 h-4 text-blue-400 shrink-0" />;
}

function severityBadge(severity: string) {
  const cls =
    severity === "error"
      ? "bg-red-900/40 text-red-300 border-red-700"
      : severity === "warning"
      ? "bg-amber-900/40 text-amber-300 border-amber-700"
      : "bg-blue-900/40 text-blue-300 border-blue-700";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>
      {severity}
    </span>
  );
}

const PROPOSAL_COLORS: Record<string, string> = {
  add_class: "bg-violet-900/40 text-violet-300 border-violet-700",
  merge_class: "bg-blue-900/40 text-blue-300 border-blue-700",
  rename_class: "bg-cyan-900/40 text-cyan-300 border-cyan-700",
  add_relationship: "bg-green-900/40 text-green-300 border-green-700",
};

function issueTypeLabel(t: string): string {
  return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Metric Card ───────────────────────────────────────────────────────────────

function BigMetricCard({
  label,
  value,
  color,
  subtitle,
}: {
  label: string;
  value: string;
  color: string;
  subtitle?: string;
}) {
  return (
    <div className="card flex flex-col gap-1">
      <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">{label}</p>
      <p className={`text-4xl font-bold ${color}`}>{value}</p>
      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}

function CountCard({ label, value, sub }: { label: string; value: number; sub?: string }) {
  return (
    <div className="card flex flex-col gap-1">
      <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">{label}</p>
      <p className="text-3xl font-bold text-slate-100">{value.toLocaleString()}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ── Issue Card ────────────────────────────────────────────────────────────────

function IssueCard({ issue }: { issue: KnowledgeIssue }) {
  const [expanded, setExpanded] = useState(false);
  const detail = issue.detail ?? {};
  const hasDetail = Object.keys(detail).length > 0;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className="flex items-start gap-3">
        {severityIcon(issue.severity)}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            {severityBadge(issue.severity)}
            <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">
              {issueTypeLabel(issue.issue_type)}
            </span>
          </div>
          <p className="text-sm text-slate-200">{issue.description}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
            {issue.document_id && (
              <span>doc: {issue.document_id.slice(0, 8)}…</span>
            )}
            <span>{relativeTime(issue.detected_at)}</span>
            <span className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-600">
              {issue.status}
            </span>
          </div>
          {hasDetail && (
            <button
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 mt-2"
              onClick={() => setExpanded((e) => !e)}
            >
              {expanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
              Detail
            </button>
          )}
          {expanded && hasDetail && (
            <div className="mt-2 bg-slate-800/60 rounded-lg p-2 font-mono text-xs text-slate-400 space-y-0.5">
              {Object.entries(detail).map(([k, v]) => (
                <div key={k}>
                  <span className="text-slate-500">{k}:</span>{" "}
                  <span className="text-slate-300">{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Proposal Card ─────────────────────────────────────────────────────────────

function ProposalCard({
  proposal,
  onApply,
  onDismiss,
}: {
  proposal: OntologyProposal;
  onApply: (id: string) => void;
  onDismiss: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState<"apply" | "dismiss" | null>(null);
  const detail = proposal.detail ?? {};
  const colorCls =
    PROPOSAL_COLORS[proposal.proposal_type] ??
    "bg-slate-800 text-slate-400 border-slate-700";

  async function handleApply() {
    setBusy("apply");
    await onApply(proposal.id);
    setBusy(null);
  }

  async function handleDismiss() {
    setBusy("dismiss");
    await onDismiss(proposal.id);
    setBusy(null);
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <span
          className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 mt-0.5 ${colorCls}`}
        >
          {proposal.proposal_type}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-200 mb-1">{proposal.description}</p>
          <button
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300"
            onClick={() => setExpanded((e) => !e)}
          >
            {expanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            Rationale
          </button>
          {expanded && (
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              {proposal.rationale}
            </p>
          )}
          {Object.keys(detail).length > 0 && expanded && (
            <div className="mt-2 bg-slate-800/60 rounded-lg p-2 font-mono text-xs text-slate-400 space-y-0.5">
              {Object.entries(detail).map(([k, v]) =>
                v != null ? (
                  <div key={k}>
                    <span className="text-slate-500">{k}:</span>{" "}
                    <span className="text-slate-300">{String(v)}</span>
                  </div>
                ) : null
              )}
            </div>
          )}
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleApply}
              disabled={busy !== null}
              className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
            >
              {busy === "apply" && <Loader2 className="w-3 h-3 animate-spin" />}
              Apply
            </button>
            <button
              onClick={handleDismiss}
              disabled={busy !== null}
              className="text-xs bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-400 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
            >
              {busy === "dismiss" && <Loader2 className="w-3 h-3 animate-spin" />}
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Heatmap Tab ───────────────────────────────────────────────────────────────

function HeatmapTab({ entities }: { entities: Entity[] }) {
  // Group by entity_type, compute avg confidence
  const typeMap: Record<string, { total: number; count: number }> = {};
  for (const e of entities) {
    if (!typeMap[e.entity_type]) typeMap[e.entity_type] = { total: 0, count: 0 };
    typeMap[e.entity_type].total += e.confidence;
    typeMap[e.entity_type].count += 1;
  }

  const rows = Object.entries(typeMap)
    .map(([type, { total, count }]) => ({
      type,
      count,
      avg: total / count,
    }))
    .sort((a, b) => a.avg - b.avg);

  const lowConf = [...entities]
    .filter((e) => e.confidence < 0.7)
    .sort((a, b) => a.confidence - b.confidence)
    .slice(0, 20);

  if (entities.length === 0) {
    return (
      <div className="text-center py-16 text-slate-600">
        <Activity className="w-10 h-10 mx-auto mb-3 opacity-30" />
        <p className="text-sm">No entities found. Ingest and extract entities first.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Confidence bars by entity type */}
      <div>
        <h3 className="text-sm font-semibold text-slate-300 mb-4">
          Average Confidence by Entity Type
        </h3>
        <div className="space-y-3">
          {rows.map(({ type, count, avg }) => (
            <div key={type} className="flex items-center gap-3">
              <span className="text-sm text-slate-400 w-28 shrink-0 truncate" title={type}>
                {type}
              </span>
              <div className="flex-1 bg-slate-800 rounded-full h-5 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${barColor(avg)}`}
                  style={{ width: `${(avg * 100).toFixed(1)}%` }}
                />
              </div>
              <span className={`text-xs font-mono w-10 text-right ${accuracyColor(avg)}`}>
                {(avg * 100).toFixed(0)}%
              </span>
              <span className="text-xs text-slate-500 w-14 text-right">
                {count} entities
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Low confidence entity list */}
      {lowConf.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">
            Low Confidence Entities (top {lowConf.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left">
                  <th className="pb-2 text-xs text-slate-500 font-medium pr-4">Entity</th>
                  <th className="pb-2 text-xs text-slate-500 font-medium pr-4">Type</th>
                  <th className="pb-2 text-xs text-slate-500 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {lowConf.map((e) => (
                  <tr key={e.id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                    <td className="py-2 pr-4 text-slate-300 truncate max-w-[180px]">
                      {e.name}
                    </td>
                    <td className="py-2 pr-4">
                      <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">
                        {e.entity_type}
                      </span>
                    </td>
                    <td className="py-2">
                      <span className={`text-xs font-mono ${accuracyColor(e.confidence)}`}>
                        {(e.confidence * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function KnowledgeHealthPage() {
  const [activeTab, setActiveTab] = useState<Tab>("metrics");
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [issues, setIssues] = useState<KnowledgeIssue[]>([]);
  const [proposals, setProposals] = useState<OntologyProposal[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);

  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<AnalysisResult | null>(null);

  // Issue filters
  const [filterType, setFilterType] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");

  // Analysis options
  const [autoCorrect, setAutoCorrect] = useState(false);
  const [threshold, setThreshold] = useState(0.5);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, issueRes, propRes, entRes] = await Promise.all([
        getMetrics(),
        listIssues({ status: "open" }),
        listProposals("pending"),
        listEntities(),
      ]);
      setMetrics(m);
      setIssues(issueRes.issues);
      setProposals(propRes.proposals);
      setEntities(entRes.entities);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function handleAnalyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await triggerAnalysis({
        auto_correct: autoCorrect,
        confidence_threshold: threshold,
      });
      setLastResult(result);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleApply(id: string) {
    try {
      await applyProposal(id);
      setProposals((prev) => prev.filter((p) => p.id !== id));
      // Refresh metrics since ontology class count may change
      const m = await getMetrics();
      setMetrics(m);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply proposal");
    }
  }

  async function handleDismiss(id: string) {
    try {
      await dismissProposal(id);
      setProposals((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to dismiss proposal");
    }
  }

  const filteredIssues = issues.filter((i) => {
    if (filterType && i.issue_type !== filterType) return false;
    if (filterSeverity && i.severity !== filterSeverity) return false;
    return true;
  });

  const tabs: { id: Tab; label: string }[] = [
    { id: "metrics", label: "Metrics" },
    { id: "issues", label: `Issues (${issues.length})` },
    { id: "proposals", label: `Proposals (${proposals.length})` },
    { id: "heatmap", label: "Confidence Heatmap" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Knowledge Health Dashboard</h1>
            <p className="text-sm text-slate-400">
              Evaluate graph quality, detect issues, and evolve your ontology
            </p>
          </div>
        </div>

        {/* Analysis controls */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={autoCorrect}
              onChange={(e) => setAutoCorrect(e.target.checked)}
              className="w-4 h-4 rounded accent-blue-500"
            />
            Auto-correct
          </label>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span>Threshold</span>
            <input
              type="number"
              min={0}
              max={1}
              step={0.1}
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-16 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 text-sm"
            />
          </div>
          <button
            onClick={loadAll}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            {analyzing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            {analyzing ? "Analyzing…" : "Run Analysis"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 bg-red-900/20 border border-red-800 rounded-xl px-4 py-3 text-sm text-red-300 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Last analysis result banner */}
      {lastResult && (
        <div className="flex items-center gap-4 bg-green-900/20 border border-green-800 rounded-xl px-4 py-3 text-sm text-green-300 mb-4">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>
            Analysis complete in {lastResult.duration_ms}ms —{" "}
            {lastResult.issues_detected} issues, {lastResult.proposals_generated} proposals,{" "}
            {lastResult.auto_corrections_applied} corrections
          </span>
          <button
            className="ml-auto text-green-500 hover:text-green-300"
            onClick={() => setLastResult(null)}
          >
            ×
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-800 mb-6">
        <div className="flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2.5 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
                activeTab === t.id
                  ? "border-brand-500 text-brand-400"
                  : "border-transparent text-slate-500 hover:text-slate-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && !metrics && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-slate-500 animate-spin" />
        </div>
      )}

      {/* ── Tab: Metrics ── */}
      {activeTab === "metrics" && metrics && (
        <div className="space-y-4">
          {/* Accuracy metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <BigMetricCard
              label="Entity Accuracy"
              value={pct(metrics.entity_accuracy)}
              color={accuracyColor(metrics.entity_accuracy)}
              subtitle={`${metrics.low_confidence_entities} low-confidence`}
            />
            <BigMetricCard
              label="Relationship Accuracy"
              value={pct(metrics.relationship_accuracy)}
              color={accuracyColor(metrics.relationship_accuracy)}
              subtitle={`${metrics.low_confidence_relationships} low-confidence`}
            />
            <BigMetricCard
              label="Ontology Coverage"
              value={pct(metrics.ontology_coverage)}
              color={accuracyColor(metrics.ontology_coverage)}
              subtitle={`${metrics.unique_entity_types} unique types`}
            />
            <BigMetricCard
              label="Graph Completeness"
              value={metrics.graph_completeness.toFixed(2)}
              color={accuracyColor(Math.min(metrics.graph_completeness / 2, 1))}
              subtitle="avg rels per entity"
            />
          </div>

          {/* Counts row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <CountCard label="Total Entities" value={metrics.entity_count} />
            <CountCard label="Total Relationships" value={metrics.relationship_count} />
            <CountCard
              label="Open Issues"
              value={issues.length}
              sub={`${metrics.duplicate_entities} duplicates, ${metrics.orphan_entities} orphans`}
            />
            <CountCard label="Pending Proposals" value={proposals.length} />
          </div>

          {/* Graph DB + Ontology */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card space-y-3">
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-400" />
                Knowledge Graph (Neo4j)
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500">Nodes</p>
                  <p className="text-2xl font-bold text-slate-100">
                    {metrics.neo4j_node_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Edges</p>
                  <p className="text-2xl font-bold text-slate-100">
                    {metrics.neo4j_edge_count.toLocaleString()}
                  </p>
                </div>
              </div>
              {metrics.neo4j_node_count === 0 && (
                <p className="text-xs text-slate-500 italic">
                  Build the graph to populate Neo4j metrics
                </p>
              )}
            </div>
            <div className="card space-y-3">
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-violet-400" />
                Ontology
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500">Classes</p>
                  <p className="text-2xl font-bold text-slate-100">
                    {metrics.ontology_class_count}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Unique Entity Types</p>
                  <p className="text-2xl font-bold text-slate-100">
                    {metrics.unique_entity_types}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${barColor(metrics.ontology_coverage)}`}
                    style={{ width: pct(metrics.ontology_coverage) }}
                  />
                </div>
                <span className={`text-xs font-mono ${accuracyColor(metrics.ontology_coverage)}`}>
                  {pct(metrics.ontology_coverage)} covered
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Issues ── */}
      {activeTab === "issues" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-300"
            >
              <option value="">All types</option>
              <option value="low_confidence_entity">Low Confidence Entity</option>
              <option value="low_confidence_relationship">Low Confidence Relationship</option>
              <option value="duplicate_entity">Duplicate Entity</option>
              <option value="orphan_entity">Orphan Entity</option>
              <option value="unknown_entity_type">Unknown Entity Type</option>
              <option value="sparse_relationships">Sparse Relationships</option>
            </select>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-300"
            >
              <option value="">All severities</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
            <span className="text-xs text-slate-500">
              {filteredIssues.length} / {issues.length} issues
            </span>
          </div>

          {filteredIssues.length === 0 ? (
            <div className="text-center py-16 text-slate-600">
              <CheckCircle2 className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">
                {issues.length === 0
                  ? "No issues detected. Run Analysis to scan the knowledge graph."
                  : "No issues match the current filters."}
              </p>
              {issues.length === 0 && (
                <button
                  onClick={handleAnalyze}
                  className="mt-4 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg"
                >
                  Run Analysis
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredIssues.map((issue) => (
                <IssueCard key={issue.id} issue={issue} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Proposals ── */}
      {activeTab === "proposals" && (
        <div className="space-y-4">
          {proposals.length === 0 ? (
            <div className="text-center py-16 text-slate-600">
              <GitBranch className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">
                No pending proposals. Run Analysis to generate ontology evolution proposals.
              </p>
              <button
                onClick={handleAnalyze}
                className="mt-4 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg"
              >
                Generate Proposals
              </button>
            </div>
          ) : (
            <>
              <p className="text-sm text-slate-400">
                {proposals.length} proposals pending review. Applying an{" "}
                <code className="text-xs bg-slate-800 px-1 rounded">add_class</code> proposal
                registers the class in the active ontology immediately.
              </p>
              <div className="space-y-3">
                {proposals.map((p) => (
                  <ProposalCard
                    key={p.id}
                    proposal={p}
                    onApply={handleApply}
                    onDismiss={handleDismiss}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Tab: Heatmap ── */}
      {activeTab === "heatmap" && <HeatmapTab entities={entities} />}
    </div>
  );
}
