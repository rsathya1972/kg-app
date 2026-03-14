"use client";

import { useState, useRef } from "react";
import {
  Brain,
  Send,
  ChevronDown,
  ChevronRight,
  Network,
  FileText,
  GitBranch,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Circle,
  Sparkles,
} from "lucide-react";
import { graphRagQuery } from "@/lib/api";
import type {
  GraphRAGResponse,
  GraphRAGNode,
  GraphRAGEdge,
  GraphRAGChunk,
  ReasoningStep,
} from "@/lib/types";

// ── Example questions ─────────────────────────────────────────────────────────

const EXAMPLE_QUESTIONS = [
  "Which companies depend on AWS?",
  "Which contracts expire next quarter?",
  "Which customers use product X?",
  "What technologies are used by the engineering team?",
  "Which people are connected to cloud infrastructure?",
];

// ── Helpers ───────────────────────────────────────────────────────────────────

const STEP_ICONS: Record<string, React.ReactNode> = {
  ontology_matching: <GitBranch className="w-4 h-4" />,
  graph_traversal: <Network className="w-4 h-4" />,
  vector_retrieval: <FileText className="w-4 h-4" />,
  synthesis: <Sparkles className="w-4 h-4" />,
};

const STEP_LABELS: Record<string, string> = {
  ontology_matching: "Ontology Matching",
  graph_traversal: "Graph Traversal",
  vector_retrieval: "Vector Retrieval",
  synthesis: "Answer Synthesis",
};

const NODE_TYPE_COLORS: Record<string, string> = {
  Person: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  Organization: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  Company: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  Technology: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  Location: "bg-green-500/20 text-green-300 border-green-500/30",
  Concept: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  Event: "bg-pink-500/20 text-pink-300 border-pink-500/30",
};

function nodeColor(type: string): string {
  return (
    NODE_TYPE_COLORS[type] ??
    "bg-slate-500/20 text-slate-300 border-slate-500/30"
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ReasoningTrace({ steps }: { steps: ReasoningStep[] }) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  return (
    <div className="space-y-2">
      {steps.map((step, i) => (
        <div
          key={i}
          className="bg-slate-800/60 border border-slate-700 rounded-lg overflow-hidden"
        >
          <button
            className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-700/40 transition-colors"
            onClick={() => setExpanded((e) => ({ ...e, [i]: !e[i] }))}
          >
            <span className="text-slate-400">
              {STEP_ICONS[step.step] ?? <Circle className="w-4 h-4" />}
            </span>
            <span className="flex-1 text-sm font-medium text-slate-200">
              {STEP_LABELS[step.step] ?? step.step}
            </span>
            {step.result_count != null && (
              <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                {step.result_count} results
              </span>
            )}
            {expanded[i] ? (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-500" />
            )}
          </button>
          {expanded[i] && (
            <div className="px-4 pb-3 border-t border-slate-700/50">
              <p className="text-sm text-slate-400 mt-2">{step.description}</p>
              {step.detail && (
                <p className="text-xs text-slate-500 mt-1 font-mono">
                  {step.detail}
                </p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function GraphNodeCard({ node }: { node: GraphRAGNode }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2.5 flex items-start gap-2.5">
      <span
        className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 mt-0.5 ${nodeColor(node.entity_type)}`}
      >
        {node.entity_type}
      </span>
      <div className="min-w-0">
        <p className="text-sm text-slate-200 font-medium truncate">{node.name}</p>
        {node.confidence != null && (
          <p className="text-xs text-slate-500 mt-0.5">
            confidence: {(node.confidence * 100).toFixed(0)}%
          </p>
        )}
      </div>
    </div>
  );
}

function EdgeRow({ edge }: { edge: GraphRAGEdge }) {
  const src = edge.source_name ?? edge.source_id.slice(0, 8);
  const tgt = edge.target_name ?? edge.target_id.slice(0, 8);
  return (
    <div className="flex items-center gap-2 text-xs py-1.5 border-b border-slate-800 last:border-0">
      <span className="text-slate-300 truncate max-w-[120px]" title={src}>
        {src}
      </span>
      <span className="text-slate-600 shrink-0">──</span>
      <span className="text-cyan-400 font-mono text-[11px] shrink-0 bg-slate-800 px-1.5 py-0.5 rounded">
        {edge.type}
      </span>
      <span className="text-slate-600 shrink-0">──▶</span>
      <span className="text-slate-300 truncate max-w-[120px]" title={tgt}>
        {tgt}
      </span>
    </div>
  );
}

function ChunkCard({ chunk }: { chunk: GraphRAGChunk }) {
  const [expanded, setExpanded] = useState(false);
  const preview = chunk.text.slice(0, 160);
  const hasMore = chunk.text.length > 160;

  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400 font-medium">{chunk.filename}</span>
        <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
          {(chunk.similarity_score * 100).toFixed(1)}% match
        </span>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed">
        {expanded ? chunk.text : preview}
        {hasMore && !expanded && "…"}
      </p>
      {hasMore && (
        <button
          className="text-xs text-blue-400 hover:text-blue-300 mt-1.5"
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function KnowledgeCopilotPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GraphRAGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  async function handleSubmit() {
    const q = question.trim();
    if (!q || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await graphRagQuery(q);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold">Knowledge Copilot</h1>
          <p className="text-sm text-slate-400">
            Graph-RAG: ontology reasoning + graph traversal + vector search
          </p>
        </div>
      </div>

      {/* Question input */}
      <div className="max-w-3xl mb-6">
        <div className="relative">
          <textarea
            ref={inputRef}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a question about your knowledge graph…"
            rows={2}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 pr-12 text-sm text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !question.trim()}
            className="absolute right-3 bottom-3 w-8 h-8 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            ) : (
              <Send className="w-4 h-4 text-white" />
            )}
          </button>
        </div>

        {/* Example questions */}
        <div className="flex flex-wrap gap-2 mt-3">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => {
                setQuestion(q);
                inputRef.current?.focus();
              }}
              className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-full transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="max-w-3xl space-y-3">
          {["Matching ontology classes…", "Traversing knowledge graph…", "Retrieving document chunks…", "Synthesizing answer…"].map(
            (label, i) => (
              <div
                key={i}
                className="flex items-center gap-3 bg-slate-800/40 border border-slate-700/50 rounded-lg px-4 py-3"
              >
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin shrink-0" />
                <span className="text-sm text-slate-400">{label}</span>
              </div>
            )
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="max-w-3xl flex items-start gap-3 bg-red-900/20 border border-red-800 rounded-xl p-4 text-sm text-red-300">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Answer */}
          <div className="max-w-3xl bg-gradient-to-br from-slate-800/80 to-slate-800/40 border border-slate-700 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-sm font-semibold text-slate-200">Answer</span>
              {result.ontology_classes.length > 0 && (
                <div className="flex gap-1.5 ml-2">
                  {result.ontology_classes.map((c) => (
                    <span
                      key={c}
                      className="text-[11px] bg-violet-500/20 text-violet-300 border border-violet-500/30 px-2 py-0.5 rounded-full"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
              {result.answer}
            </p>
            {result.error && (
              <p className="text-xs text-red-400 mt-3 font-mono">{result.error}</p>
            )}
          </div>

          {/* Three-column detail grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Reasoning trace */}
            <div>
              <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <Brain className="w-4 h-4 text-violet-400" />
                Reasoning Trace
              </h3>
              <ReasoningTrace steps={result.reasoning_trace} />
              {result.cypher_used && (
                <div className="mt-3 bg-slate-900 border border-slate-700 rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1 font-medium">Cypher used</p>
                  <pre className="text-xs text-cyan-300 overflow-x-auto whitespace-pre-wrap">
                    {result.cypher_used}
                  </pre>
                </div>
              )}
            </div>

            {/* Graph nodes + edges */}
            <div>
              <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <Network className="w-4 h-4 text-blue-400" />
                Graph Nodes
                <span className="text-xs bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full">
                  {result.graph_nodes.length}
                </span>
              </h3>
              {result.graph_nodes.length === 0 ? (
                <p className="text-sm text-slate-500 italic">
                  No matching graph nodes found. Build the graph first.
                </p>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {result.graph_nodes.map((n) => (
                    <GraphNodeCard key={n.id} node={n} />
                  ))}
                </div>
              )}

              {result.graph_edges.length > 0 && (
                <>
                  <h3 className="text-sm font-semibold text-slate-300 mt-5 mb-3 flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-cyan-400" />
                    Relationships
                    <span className="text-xs bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full">
                      {result.graph_edges.length}
                    </span>
                  </h3>
                  <div className="bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1 max-h-48 overflow-y-auto">
                    {result.graph_edges.map((e) => (
                      <EdgeRow key={e.id} edge={e} />
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Document chunks */}
            <div>
              <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-green-400" />
                Document Chunks
                <span className="text-xs bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full">
                  {result.document_chunks.length}
                </span>
              </h3>
              {result.document_chunks.length === 0 ? (
                <p className="text-sm text-slate-500 italic">
                  No document chunks found. Embed documents first via Vector Memory.
                </p>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                  {result.document_chunks.map((c) => (
                    <ChunkCard key={c.chunk_id} chunk={c} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div className="max-w-3xl text-center py-16 text-slate-600">
          <Brain className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-sm">Ask a question to start the Graph-RAG retrieval pipeline.</p>
          <p className="text-xs mt-2">
            The system will reason over ontology classes, traverse the knowledge graph, and
            retrieve relevant document passages before synthesizing an answer.
          </p>
        </div>
      )}
    </div>
  );
}
