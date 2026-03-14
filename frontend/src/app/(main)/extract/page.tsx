"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, ChevronDown, ChevronRight, Loader2, X, Share2 } from "lucide-react";
import { ReactFlow, ReactFlowProvider, Background, Controls, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  extractEntities,
  extractRelationships,
  listDocuments,
  listEntities,
  listRelationships,
} from "@/lib/api";
import type { Document, Entity, Relationship } from "@/lib/types";

// ── Entity type colours ───────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  Company:    "bg-blue-900 text-blue-300 border-blue-700",
  Person:     "bg-purple-900 text-purple-300 border-purple-700",
  Product:    "bg-green-900 text-green-300 border-green-700",
  Contract:   "bg-yellow-900 text-yellow-300 border-yellow-700",
  Location:   "bg-teal-900 text-teal-300 border-teal-700",
  Technology: "bg-orange-900 text-orange-300 border-orange-700",
  Policy:     "bg-pink-900 text-pink-300 border-pink-700",
  Regulation: "bg-red-900 text-red-300 border-red-700",
};

const NODE_BG: Record<string, string> = {
  Company:    "#1e3a5f",
  Person:     "#3b1f5e",
  Product:    "#14532d",
  Contract:   "#713f12",
  Location:   "#134e4a",
  Technology: "#7c2d12",
  Policy:     "#831843",
  Regulation: "#7f1d1d",
};

// ── Relationship type colours ─────────────────────────────────────────────────

const REL_COLORS: Record<string, string> = {
  WORKS_FOR:   "bg-indigo-900 text-indigo-300 border-indigo-700",
  OWNS:        "bg-emerald-900 text-emerald-300 border-emerald-700",
  USES:        "bg-orange-900 text-orange-300 border-orange-700",
  BELONGS_TO:  "bg-cyan-900 text-cyan-300 border-cyan-700",
  RENEWS:      "bg-amber-900 text-amber-300 border-amber-700",
  EXPIRES_ON:  "bg-rose-900 text-rose-300 border-rose-700",
  LOCATED_IN:  "bg-teal-900 text-teal-300 border-teal-700",
  DEPENDS_ON:  "bg-violet-900 text-violet-300 border-violet-700",
  SELLS_TO:    "bg-green-900 text-green-300 border-green-700",
  GOVERNED_BY: "bg-red-900 text-red-300 border-red-700",
};

const ENTITY_TYPES = [
  "All", "Company", "Person", "Product", "Contract",
  "Location", "Technology", "Policy", "Regulation",
];

const RELATIONSHIP_TYPES = [
  "All", "WORKS_FOR", "OWNS", "USES", "BELONGS_TO", "RENEWS",
  "EXPIRES_ON", "LOCATED_IN", "DEPENDS_ON", "SELLS_TO", "GOVERNED_BY",
];

// ── Shared sub-components ─────────────────────────────────────────────────────

function TypeBadge({ type }: { type: string }) {
  const cls = TYPE_COLORS[type] ?? "bg-slate-800 text-slate-300 border-slate-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {type}
    </span>
  );
}

function RelBadge({ type }: { type: string }) {
  const cls = REL_COLORS[type] ?? "bg-slate-800 text-slate-300 border-slate-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {type}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "bg-green-500" :
    pct >= 50 ? "bg-yellow-500" :
    "bg-red-500";
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 bg-slate-700 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

// ── Entity detail modal ───────────────────────────────────────────────────────

function EntityModal({ entity, onClose }: { entity: Entity; onClose: () => void }) {
  const attrEntries = Object.entries(entity.attributes).filter(([k]) => k !== "_evidence");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100 mb-1">{entity.name}</h2>
            <TypeBadge type={entity.entity_type} />
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="mb-4">
          <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Evidence</p>
          <blockquote className="text-sm text-slate-300 bg-slate-800 rounded-lg p-3 border-l-2 border-brand-400 italic">
            {entity.evidence_chunk || <span className="text-slate-500">No evidence captured</span>}
          </blockquote>
        </div>
        <div className="mb-4">
          <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Attributes</p>
          {attrEntries.length === 0 ? (
            <p className="text-sm text-slate-500">No attributes</p>
          ) : (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
              {attrEntries.map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs text-slate-500 capitalize">{k}</dt>
                  <dd className="text-sm text-slate-200">{String(v)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-800">
          <span>Confidence: {Math.round(entity.confidence * 100)}%</span>
          <span>ID: {entity.id.slice(0, 8)}…</span>
        </div>
      </div>
    </div>
  );
}

// ── Relationship detail modal ─────────────────────────────────────────────────

function RelModal({ rel, onClose }: { rel: Relationship; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-slate-100 font-semibold">{rel.source_entity_name}</span>
            <RelBadge type={rel.relationship_type} />
            <span className="text-slate-100 font-semibold">{rel.target_entity_name}</span>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors ml-2">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="mb-4">
          <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Evidence</p>
          <blockquote className="text-sm text-slate-300 bg-slate-800 rounded-lg p-3 border-l-2 border-brand-400 italic">
            {rel.evidence_text || <span className="text-slate-500">No evidence captured</span>}
          </blockquote>
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-800">
          <span>Confidence: {Math.round(rel.confidence * 100)}%</span>
          <span>ID: {rel.id.slice(0, 8)}…</span>
        </div>
      </div>
    </div>
  );
}

// ── Network graph builder ─────────────────────────────────────────────────────

function buildGraphElements(
  relationships: Relationship[],
  entityMap: Map<string, Entity>
): { nodes: Node[]; edges: Edge[] } {
  const nameSet = new Set<string>();
  for (const r of relationships) {
    nameSet.add(r.source_entity_name);
    nameSet.add(r.target_entity_name);
  }
  const names = Array.from(nameSet);
  const N = names.length;
  const cx = 350;
  const cy = 210;
  const R = Math.max(140, N * 28);

  const nodes: Node[] = names.map((name, i) => {
    const angle = (2 * Math.PI * i) / N - Math.PI / 2;
    const entityType = entityMap.get(name.toLowerCase())?.entity_type ?? "";
    const bg = NODE_BG[entityType] ?? "#1e293b";
    return {
      id: name,
      position: { x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle) },
      data: { label: name },
      style: {
        background: bg,
        color: "#e2e8f0",
        border: "1px solid #334155",
        borderRadius: "8px",
        fontSize: "11px",
        padding: "6px 10px",
        maxWidth: "120px",
        textAlign: "center" as const,
      },
    };
  });

  const edges: Edge[] = relationships.map((r, i) => ({
    id: `e-${i}`,
    source: r.source_entity_name,
    target: r.target_entity_name,
    label: r.relationship_type.replace("_", " "),
    style: { stroke: "#64748b", strokeWidth: 1.5 },
    labelStyle: { fill: "#94a3b8", fontSize: 9 },
    labelBgStyle: { fill: "#0f172a", fillOpacity: 0.7 },
  }));

  return { nodes, edges };
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = "entities" | "relationships";

export default function ExtractPage() {
  const [activeTab, setActiveTab] = useState<Tab>("entities");

  // Shared state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");

  // Entity state
  const [entities, setEntities] = useState<Entity[]>([]);
  const [typeFilter, setTypeFilter] = useState<string>("All");
  const [loadingEntities, setLoadingEntities] = useState(false);
  const [fetchingEntities, setFetchingEntities] = useState(false);
  const [entityError, setEntityError] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);

  // Relationship state
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [relTypeFilter, setRelTypeFilter] = useState<string>("All");
  const [loadingRel, setLoadingRel] = useState(false);
  const [fetchingRel, setFetchingRel] = useState(false);
  const [relError, setRelError] = useState<string | null>(null);
  const [selectedRel, setSelectedRel] = useState<Relationship | null>(null);

  // Load documents on mount
  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  // When doc changes, load existing entities + relationships
  useEffect(() => {
    if (!selectedDocId) {
      setEntities([]);
      setRelationships([]);
      return;
    }
    setFetchingEntities(true);
    setEntityError(null);
    listEntities({ document_id: selectedDocId })
      .then((res) => setEntities(res.entities))
      .catch(() => setEntities([]))
      .finally(() => setFetchingEntities(false));

    setFetchingRel(true);
    setRelError(null);
    listRelationships({ document_id: selectedDocId })
      .then((res) => setRelationships(res.relationships))
      .catch(() => setRelationships([]))
      .finally(() => setFetchingRel(false));
  }, [selectedDocId]);

  async function handleExtractEntities() {
    if (!selectedDocId) return;
    setLoadingEntities(true);
    setEntityError(null);
    try {
      const res = await extractEntities(selectedDocId);
      setEntities(res.entities);
      setTypeFilter("All");
    } catch (err) {
      setEntityError(err instanceof Error ? err.message : "Extraction failed");
    } finally {
      setLoadingEntities(false);
    }
  }

  async function handleExtractRelationships() {
    if (!selectedDocId) return;
    setLoadingRel(true);
    setRelError(null);
    try {
      const res = await extractRelationships(selectedDocId);
      setRelationships(res.relationships);
      setRelTypeFilter("All");
    } catch (err) {
      setRelError(err instanceof Error ? err.message : "Extraction failed");
    } finally {
      setLoadingRel(false);
    }
  }

  // Entity derived state
  const filteredEntities =
    typeFilter === "All" ? entities : entities.filter((e) => e.entity_type === typeFilter);
  const typeCounts: Record<string, number> = {};
  for (const e of entities) {
    typeCounts[e.entity_type] = (typeCounts[e.entity_type] ?? 0) + 1;
  }

  // Relationship derived state
  const filteredRels =
    relTypeFilter === "All"
      ? relationships
      : relationships.filter((r) => r.relationship_type === relTypeFilter);
  const relTypeCounts: Record<string, number> = {};
  for (const r of relationships) {
    relTypeCounts[r.relationship_type] = (relTypeCounts[r.relationship_type] ?? 0) + 1;
  }

  // Build entity name → Entity map for graph coloring
  const entityByName = new Map<string, Entity>();
  for (const e of entities) {
    entityByName.set(e.name.toLowerCase(), e);
  }

  const { nodes, edges } = buildGraphElements(relationships, entityByName);

  const onNodesChange = useCallback(() => {}, []);
  const onEdgesChange = useCallback(() => {}, []);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <Cpu className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Entity Explorer</h1>
          <p className="text-slate-500 text-sm">
            AI-powered extraction of entities and relationships
          </p>
        </div>
      </div>

      {/* Document selector */}
      <div className="card mb-4">
        <div className="relative">
          <select
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm appearance-none pr-8 focus:outline-none focus:ring-1 focus:ring-brand-500"
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
          >
            <option value="">— Select a document —</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename ?? doc.id} ({doc.word_count ?? "?"} words)
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-slate-800">
        {(["entities", "relationships"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? "border-brand-500 text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab === "entities" ? (
              <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5" />Entities{entities.length > 0 && <span className="bg-slate-700 rounded-full px-1.5 text-xs">{entities.length}</span>}</span>
            ) : (
              <span className="flex items-center gap-1.5"><Share2 className="w-3.5 h-3.5" />Relationships{relationships.length > 0 && <span className="bg-slate-700 rounded-full px-1.5 text-xs">{relationships.length}</span>}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── ENTITIES TAB ──────────────────────────────────────────────────────── */}
      {activeTab === "entities" && (
        <>
          {/* Controls */}
          <div className="card mb-4 flex justify-end">
            <button
              onClick={handleExtractEntities}
              disabled={!selectedDocId || loadingEntities}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loadingEntities ? <Loader2 className="w-4 h-4 animate-spin" /> : <Cpu className="w-4 h-4" />}
              {loadingEntities ? "Extracting…" : "Run Extraction"}
            </button>
          </div>

          {entityError && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm flex items-center justify-between">
              <span>{entityError}</span>
              <button onClick={() => setEntityError(null)}><X className="w-4 h-4" /></button>
            </div>
          )}

          {!selectedDocId ? (
            <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
              <Cpu className="w-10 h-10 text-slate-600" />
              <p className="text-slate-400 text-sm">Select a document to begin</p>
            </div>
          ) : fetchingEntities ? (
            <div className="card flex items-center justify-center py-16 gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
              <span className="text-slate-400 text-sm">Loading existing entities…</span>
            </div>
          ) : (
            <>
              {entities.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {ENTITY_TYPES.map((t) => {
                    const count = t === "All" ? entities.length : (typeCounts[t] ?? 0);
                    const active = typeFilter === t;
                    return (
                      <button
                        key={t}
                        onClick={() => setTypeFilter(t)}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                          active
                            ? "bg-brand-600 border-brand-500 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500"
                        }`}
                      >
                        {t}
                        {count > 0 && (
                          <span className={`rounded-full px-1.5 py-0.5 text-xs ${active ? "bg-brand-500" : "bg-slate-700"}`}>
                            {count}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}

              {entities.length === 0 && !loadingEntities && (
                <div className="card flex flex-col items-center justify-center gap-3 py-16">
                  <Cpu className="w-8 h-8 text-slate-600" />
                  <p className="text-slate-400 text-sm">No entities extracted yet. Click Run Extraction to start.</p>
                </div>
              )}

              {filteredEntities.length > 0 && (
                <div className="card overflow-hidden p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-800/50">
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-32">Type</th>
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Name</th>
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-36">Confidence</th>
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Evidence</th>
                        <th className="px-4 py-3 w-8" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {filteredEntities.map((entity) => (
                        <tr
                          key={entity.id}
                          className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                          onClick={() => setSelectedEntity(entity)}
                        >
                          <td className="px-4 py-3"><TypeBadge type={entity.entity_type} /></td>
                          <td className="px-4 py-3 text-slate-200 font-medium">{entity.name}</td>
                          <td className="px-4 py-3"><ConfidenceBar value={entity.confidence} /></td>
                          <td className="px-4 py-3 text-slate-400 max-w-xs">
                            <span className="line-clamp-1 text-xs">
                              {entity.evidence_chunk || <span className="text-slate-600 italic">—</span>}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-600"><ChevronRight className="w-4 h-4" /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="px-4 py-2 border-t border-slate-800 text-xs text-slate-600">
                    Showing {filteredEntities.length} of {entities.length} entities
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ── RELATIONSHIPS TAB ─────────────────────────────────────────────────── */}
      {activeTab === "relationships" && (
        <>
          {/* Controls */}
          <div className="card mb-4 flex items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              {entities.length === 0
                ? "Run entity extraction first before extracting relationships."
                : `${entities.length} entities available`}
            </p>
            <button
              onClick={handleExtractRelationships}
              disabled={!selectedDocId || loadingRel || entities.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors shrink-0"
            >
              {loadingRel ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share2 className="w-4 h-4" />}
              {loadingRel ? "Extracting…" : "Run Relationship Extraction"}
            </button>
          </div>

          {relError && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm flex items-center justify-between">
              <span>{relError}</span>
              <button onClick={() => setRelError(null)}><X className="w-4 h-4" /></button>
            </div>
          )}

          {!selectedDocId ? (
            <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
              <Share2 className="w-10 h-10 text-slate-600" />
              <p className="text-slate-400 text-sm">Select a document to begin</p>
            </div>
          ) : fetchingRel ? (
            <div className="card flex items-center justify-center py-16 gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
              <span className="text-slate-400 text-sm">Loading existing relationships…</span>
            </div>
          ) : (
            <>
              {/* Type filter pills */}
              {relationships.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {RELATIONSHIP_TYPES.map((t) => {
                    const count = t === "All" ? relationships.length : (relTypeCounts[t] ?? 0);
                    const active = relTypeFilter === t;
                    return (
                      <button
                        key={t}
                        onClick={() => setRelTypeFilter(t)}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                          active
                            ? "bg-brand-600 border-brand-500 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500"
                        }`}
                      >
                        {t}
                        {count > 0 && (
                          <span className={`rounded-full px-1.5 py-0.5 text-xs ${active ? "bg-brand-500" : "bg-slate-700"}`}>
                            {count}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Empty state */}
              {relationships.length === 0 && !loadingRel && (
                <div className="card flex flex-col items-center justify-center gap-3 py-16">
                  <Share2 className="w-8 h-8 text-slate-600" />
                  <p className="text-slate-400 text-sm">
                    No relationships extracted yet. Click Run Relationship Extraction to start.
                  </p>
                </div>
              )}

              {/* Relationship table */}
              {filteredRels.length > 0 && (
                <div className="card overflow-hidden p-0 mb-4">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-800/50">
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Source</th>
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-36">Type</th>
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Target</th>
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-28">Confidence</th>
                        <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Evidence</th>
                        <th className="px-4 py-3 w-8" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {filteredRels.map((rel) => (
                        <tr
                          key={rel.id}
                          className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                          onClick={() => setSelectedRel(rel)}
                        >
                          <td className="px-4 py-3 text-slate-200 font-medium">{rel.source_entity_name}</td>
                          <td className="px-4 py-3"><RelBadge type={rel.relationship_type} /></td>
                          <td className="px-4 py-3 text-slate-200 font-medium">{rel.target_entity_name}</td>
                          <td className="px-4 py-3"><ConfidenceBar value={rel.confidence} /></td>
                          <td className="px-4 py-3 text-slate-400 max-w-xs">
                            <span className="line-clamp-1 text-xs">
                              {rel.evidence_text || <span className="text-slate-600 italic">—</span>}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-600"><ChevronRight className="w-4 h-4" /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="px-4 py-2 border-t border-slate-800 text-xs text-slate-600">
                    Showing {filteredRels.length} of {relationships.length} relationships
                  </div>
                </div>
              )}

              {/* Network graph */}
              {relationships.length > 0 && (
                <div className="card p-0 overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
                    <Share2 className="w-4 h-4 text-brand-400" />
                    <span className="text-sm font-medium text-slate-300">Network Graph</span>
                    <span className="text-xs text-slate-500 ml-1">({nodes.length} nodes · {edges.length} edges)</span>
                  </div>
                  <div style={{ height: 420 }}>
                    <ReactFlowProvider>
                      <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        fitView
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable={false}
                        proOptions={{ hideAttribution: true }}
                      >
                        <Background color="#1e293b" gap={20} />
                        <Controls showInteractive={false} />
                      </ReactFlow>
                    </ReactFlowProvider>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* Modals */}
      {selectedEntity && <EntityModal entity={selectedEntity} onClose={() => setSelectedEntity(null)} />}
      {selectedRel && <RelModal rel={selectedRel} onClose={() => setSelectedRel(null)} />}
    </div>
  );
}
