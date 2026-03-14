"use client";

import { useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  GitBranch,
  Loader2,
  X,
} from "lucide-react";
import {
  generateOntology,
  getOntologyVersion,
  listDocuments,
  listOntologyVersions,
} from "@/lib/api";
import type {
  Document,
  OntologyClassDiscovered,
  OntologyContent,
  OntologyRelationshipDiscovered,
  OntologyVersionDetail,
  OntologyVersionSummary,
} from "@/lib/types";

// ── Relationship predicate badge colours (reuse pattern from extract page) ────

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

const DOMAIN_HINTS = ["telecom", "insurance", "saas", "healthcare", "finance"];

type Tab = "classes" | "relationships" | "json";

// ── Sub-components ────────────────────────────────────────────────────────────

function RelBadge({ type }: { type: string }) {
  const cls = REL_COLORS[type] ?? "bg-slate-800 text-slate-300 border-slate-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {type}
    </span>
  );
}

function ClassCard({ cls }: { cls: OntologyClassDiscovered }) {
  return (
    <div className="card p-0 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between gap-2">
        <span className="font-semibold text-slate-100">{cls.name}</span>
        {cls.parent_class && (
          <span className="text-xs bg-slate-800 border border-slate-700 text-slate-400 rounded px-2 py-0.5">
            extends {cls.parent_class}
          </span>
        )}
      </div>

      {cls.description && (
        <p className="px-4 pt-3 text-sm text-slate-400 italic">{cls.description}</p>
      )}

      {cls.attributes.length > 0 && (
        <div className="px-4 pt-3">
          <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Attributes</p>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="text-left pb-1 text-slate-500 font-medium w-1/3">Name</th>
                <th className="text-left pb-1 text-slate-500 font-medium w-1/4">Type</th>
                <th className="text-left pb-1 text-slate-500 font-medium">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {cls.attributes.map((attr) => (
                <tr key={attr.name}>
                  <td className="py-1.5 text-slate-300 font-mono">{attr.name}</td>
                  <td className="py-1.5 text-brand-400">{attr.type}</td>
                  <td className="py-1.5 text-slate-500">{attr.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {cls.synonyms.length > 0 && (
        <div className="px-4 pt-3 pb-3 flex flex-wrap gap-1.5">
          <span className="text-xs text-slate-500 mr-1">Also known as:</span>
          {cls.synonyms.map((s) => (
            <span
              key={s}
              className="text-xs bg-slate-800 border border-slate-700 text-slate-400 rounded-full px-2 py-0.5"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      {cls.attributes.length === 0 && cls.synonyms.length === 0 && !cls.description && (
        <p className="px-4 py-3 text-xs text-slate-600 italic">No details available</p>
      )}

      {(cls.attributes.length > 0 || cls.synonyms.length > 0) && cls.synonyms.length === 0 && (
        <div className="pb-3" />
      )}
    </div>
  );
}

function ClassesTab({ ontology }: { ontology: OntologyContent }) {
  if (ontology.classes.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center gap-3 py-16">
        <GitBranch className="w-8 h-8 text-slate-600" />
        <p className="text-slate-400 text-sm">No classes in this ontology version.</p>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {ontology.classes.map((cls) => (
        <ClassCard key={cls.name} cls={cls} />
      ))}
    </div>
  );
}

function RelationshipsTab({ rels }: { rels: OntologyRelationshipDiscovered[] }) {
  if (rels.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center gap-3 py-16">
        <GitBranch className="w-8 h-8 text-slate-600" />
        <p className="text-slate-400 text-sm">No relationships in this ontology version.</p>
      </div>
    );
  }
  return (
    <div className="card overflow-hidden p-0">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800 bg-slate-800/50">
            <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Source Class</th>
            <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-36">Predicate</th>
            <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Target Class</th>
            <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Description</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {rels.map((r, i) => (
            <tr key={i} className="hover:bg-slate-800/30 transition-colors">
              <td className="px-4 py-3 text-slate-200 font-medium">{r.source_class}</td>
              <td className="px-4 py-3"><RelBadge type={r.predicate} /></td>
              <td className="px-4 py-3 text-slate-200 font-medium">{r.target_class}</td>
              <td className="px-4 py-3 text-slate-400 text-xs">{r.description ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function JsonTab({ ontology }: { ontology: OntologyContent }) {
  return (
    <pre className="font-mono text-sm text-green-400 bg-slate-950 p-4 rounded-lg overflow-auto max-h-[600px] border border-slate-800">
      {JSON.stringify(ontology, null, 2)}
    </pre>
  );
}

// ── Version list item ─────────────────────────────────────────────────────────

function VersionItem({
  v,
  active,
  onClick,
}: {
  v: OntologyVersionSummary;
  active: boolean;
  onClick: () => void;
}) {
  const date = new Date(v.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
        active
          ? "bg-brand-900/30 border-brand-700 text-brand-300"
          : "bg-slate-800/40 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-sm">v{v.version}</span>
        {v.domain_hint && (
          <span className="text-xs bg-slate-700 rounded px-1.5 py-0.5">{v.domain_hint}</span>
        )}
      </div>
      <div className="text-xs mt-0.5 opacity-75">
        {v.classes_count} classes · {v.relationships_count} rels
      </div>
      <div className="text-xs mt-0.5 opacity-50">{date}</div>
    </button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function OntologyPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [domainHint, setDomainHint] = useState<string>("");
  const [versions, setVersions] = useState<OntologyVersionSummary[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<OntologyVersionDetail | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("classes");
  const [generating, setGenerating] = useState(false);
  const [fetchingVersions, setFetchingVersions] = useState(false);
  const [loadingVersion, setLoadingVersion] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load documents on mount
  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  // When document changes, load existing versions
  useEffect(() => {
    if (!selectedDocId) {
      setVersions([]);
      setSelectedVersion(null);
      return;
    }
    setFetchingVersions(true);
    setError(null);
    listOntologyVersions({ document_id: selectedDocId })
      .then(async (res) => {
        setVersions(res.versions);
        // Auto-load the most recent version
        if (res.versions.length > 0) {
          const detail = await getOntologyVersion(res.versions[0].id);
          setSelectedVersion(detail);
        } else {
          setSelectedVersion(null);
        }
      })
      .catch(() => {
        setVersions([]);
        setSelectedVersion(null);
      })
      .finally(() => setFetchingVersions(false));
  }, [selectedDocId]);

  async function handleGenerate() {
    if (!selectedDocId) return;
    setGenerating(true);
    setError(null);
    try {
      const detail = await generateOntology({
        document_id: selectedDocId,
        domain_hint: domainHint || undefined,
      });
      setVersions((prev) => [detail, ...prev]);
      setSelectedVersion(detail);
      setActiveTab("classes");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSelectVersion(id: string) {
    setLoadingVersion(true);
    try {
      const detail = await getOntologyVersion(id);
      setSelectedVersion(detail);
    } catch {
      // keep current
    } finally {
      setLoadingVersion(false);
    }
  }

  const hasVersions = versions.length > 0;
  const showSidebar = hasVersions && selectedVersion !== null;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <GitBranch className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Ontology Explorer</h1>
          <p className="text-slate-500 text-sm">
            AI-generated domain ontology from extracted entities and relationships
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="card mb-4 flex flex-col sm:flex-row gap-3 items-start sm:items-end">
        {/* Document selector */}
        <div className="relative flex-1 min-w-0">
          <label className="block text-xs text-slate-500 mb-1">Document</label>
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
          <ChevronDown className="absolute right-2 bottom-2.5 w-4 h-4 text-slate-500 pointer-events-none" />
        </div>

        {/* Domain hint */}
        <div className="flex-1 min-w-0">
          <label className="block text-xs text-slate-500 mb-1">Domain Hint (optional)</label>
          <input
            type="text"
            value={domainHint}
            onChange={(e) => setDomainHint(e.target.value)}
            placeholder="e.g. telecom, saas, insurance"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder-slate-600"
          />
          {/* Quick-pick pills */}
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {DOMAIN_HINTS.map((hint) => (
              <button
                key={hint}
                onClick={() => setDomainHint(domainHint === hint ? "" : hint)}
                className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                  domainHint === hint
                    ? "bg-brand-600 border-brand-500 text-white"
                    : "bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300"
                }`}
              >
                {hint}
              </button>
            ))}
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={!selectedDocId || generating}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors shrink-0 self-end mb-0.5"
        >
          {generating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <GitBranch className="w-4 h-4" />
          )}
          {generating ? "Generating…" : "Generate Ontology"}
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)}><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* Main content */}
      {!selectedDocId ? (
        <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
          <GitBranch className="w-10 h-10 text-slate-600" />
          <p className="text-slate-400 text-sm">Select a document to begin</p>
        </div>
      ) : fetchingVersions ? (
        <div className="card flex items-center justify-center py-16 gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
          <span className="text-slate-400 text-sm">Loading ontology versions…</span>
        </div>
      ) : !hasVersions ? (
        <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
          <GitBranch className="w-10 h-10 text-slate-600" />
          <div className="text-center">
            <p className="text-slate-300 font-medium">No ontology generated yet</p>
            <p className="text-slate-500 text-sm mt-1">
              Click Generate Ontology to discover the domain ontology from extracted entities and relationships.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex gap-4 items-start">
          {/* Version sidebar */}
          <div className="w-52 shrink-0 flex flex-col gap-2">
            <p className="text-xs text-slate-500 uppercase tracking-wide px-1">Versions</p>
            {versions.map((v) => (
              <VersionItem
                key={v.id}
                v={v}
                active={selectedVersion?.id === v.id}
                onClick={() => handleSelectVersion(v.id)}
              />
            ))}
          </div>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {loadingVersion ? (
              <div className="card flex items-center justify-center py-16 gap-3">
                <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
                <span className="text-slate-400 text-sm">Loading version…</span>
              </div>
            ) : selectedVersion ? (
              <>
                {/* Version header */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-200">
                      v{selectedVersion.version}
                    </span>
                    <span className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-0.5 font-medium">
                      {selectedVersion.ontology.domain}
                    </span>
                    {selectedVersion.domain_hint && (
                      <span className="text-xs text-slate-500">hint: {selectedVersion.domain_hint}</span>
                    )}
                  </div>
                  <div className="ml-auto flex items-center gap-3 text-xs text-slate-500">
                    <span>{selectedVersion.classes_count} classes</span>
                    <span>{selectedVersion.relationships_count} relationships</span>
                    <span>{selectedVersion.model_used}</span>
                  </div>
                </div>

                {/* Tab bar */}
                <div className="flex gap-1 mb-4 border-b border-slate-800">
                  {(["classes", "relationships", "json"] as Tab[]).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
                        activeTab === tab
                          ? "border-brand-500 text-brand-400"
                          : "border-transparent text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      {tab === "classes" && (
                        <span className="flex items-center gap-1.5">
                          Classes
                          <span className="bg-slate-700 rounded-full px-1.5 text-xs">
                            {selectedVersion.ontology.classes.length}
                          </span>
                        </span>
                      )}
                      {tab === "relationships" && (
                        <span className="flex items-center gap-1.5">
                          Relationships
                          <span className="bg-slate-700 rounded-full px-1.5 text-xs">
                            {selectedVersion.ontology.relationships.length}
                          </span>
                        </span>
                      )}
                      {tab === "json" && "JSON"}
                    </button>
                  ))}
                </div>

                {/* Tab content */}
                {activeTab === "classes" && (
                  <ClassesTab ontology={selectedVersion.ontology} />
                )}
                {activeTab === "relationships" && (
                  <RelationshipsTab rels={selectedVersion.ontology.relationships} />
                )}
                {activeTab === "json" && (
                  <JsonTab ontology={selectedVersion.ontology} />
                )}
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
