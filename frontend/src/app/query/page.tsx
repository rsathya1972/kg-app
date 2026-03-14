"use client";

import { useState } from "react";
import { Search, Loader2, X, Code, MessageSquare, Database, ChevronRight } from "lucide-react";
import { queryKnowledgeGraph } from "@/lib/api";
import type { QueryResponse } from "@/lib/types";

// ── Example queries ───────────────────────────────────────────────────────────

const EXAMPLES = [
  "What entities are connected to Acme Corporation?",
  "Show me all technology relationships in the graph",
  "Which companies have contractual relationships?",
  "Find all products owned by a company",
];

// ── Cypher block ──────────────────────────────────────────────────────────────

function CypherBlock({ cypher }: { cypher: string }) {
  return (
    <div className="card p-0 overflow-hidden mb-4">
      <div className="px-4 py-2 border-b border-slate-800 flex items-center gap-2">
        <Code className="w-4 h-4 text-brand-400" />
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">Generated Cypher</span>
      </div>
      <pre className="px-4 py-3 text-xs text-green-300 bg-slate-950 overflow-x-auto whitespace-pre-wrap">
        {cypher}
      </pre>
    </div>
  );
}

// ── Results table ─────────────────────────────────────────────────────────────

function ResultsTable({ results }: { results: Record<string, unknown>[] }) {
  if (results.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center gap-2 py-10 mb-4">
        <Database className="w-8 h-8 text-slate-700" />
        <p className="text-slate-500 text-sm">No graph records returned</p>
      </div>
    );
  }

  const keys = Object.keys(results[0]);

  return (
    <div className="card p-0 overflow-hidden mb-4">
      <div className="px-4 py-2 border-b border-slate-800 flex items-center gap-2">
        <Database className="w-4 h-4 text-brand-400" />
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
          Graph Results
        </span>
        <span className="text-xs text-slate-600 ml-auto">{results.length} row{results.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-800/40">
              {keys.map((k) => (
                <th key={k} className="text-left px-4 py-2 text-xs text-slate-500 uppercase tracking-wide font-medium">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {results.map((row, i) => (
              <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                {keys.map((k) => (
                  <td key={k} className="px-4 py-2 text-slate-300 text-xs">
                    {row[k] == null
                      ? <span className="text-slate-600 italic">null</span>
                      : typeof row[k] === "object"
                      ? <code className="text-xs text-slate-400">{JSON.stringify(row[k])}</code>
                      : String(row[k])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── RAG answer block ──────────────────────────────────────────────────────────

function RagAnswer({ answer, sources }: { answer: string; sources: Record<string, unknown>[] }) {
  return (
    <div className="card mb-4">
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare className="w-4 h-4 text-brand-400" />
        <span className="text-sm font-medium text-slate-300">AI Answer</span>
      </div>
      <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">{answer}</p>
      {sources.length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400 transition-colors">
            {sources.length} source chunk{sources.length !== 1 ? "s" : ""}
          </summary>
          <ul className="mt-2 space-y-1">
            {sources.map((s, i) => (
              <li key={i} className="text-xs text-slate-500 flex items-start gap-1">
                <ChevronRight className="w-3 h-3 mt-0.5 shrink-0" />
                <span className="line-clamp-2">{String(s.text ?? s.chunk_id ?? JSON.stringify(s))}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleQuery() {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await queryKnowledgeGraph(q);
      if (res.error) {
        setError(res.error);
      }
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleQuery();
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <Search className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Query</h1>
          <p className="text-slate-500 text-sm">Natural language → Cypher + RAG-grounded answers</p>
        </div>
      </div>

      {/* Input card */}
      <div className="card mb-4">
        <label className="block text-xs text-slate-500 uppercase tracking-wide mb-2">
          Natural language query
        </label>
        <textarea
          rows={3}
          placeholder="Ask a question about your knowledge graph…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
        />
        <div className="flex items-center justify-between mt-3">
          <p className="text-xs text-slate-600">⌘+Enter to submit</p>
          <button
            onClick={handleQuery}
            disabled={!query.trim() || loading}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? "Querying…" : "Run Query"}
          </button>
        </div>
      </div>

      {/* Example queries */}
      {!result && !loading && (
        <div className="mb-6">
          <p className="text-xs text-slate-600 uppercase tracking-wide mb-2">Example queries</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setQuery(ex)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)}>
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="card flex items-center justify-center py-16 gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
          <span className="text-slate-400 text-sm">Translating to Cypher and querying the graph…</span>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {result.cypher && <CypherBlock cypher={result.cypher} />}
          <ResultsTable results={result.results} />
          {result.answer && <RagAnswer answer={result.answer} sources={result.sources} />}

          {!result.cypher && !result.answer && !error && (
            <div className="card flex flex-col items-center justify-center gap-3 py-12">
              <Search className="w-8 h-8 text-slate-700" />
              <p className="text-slate-500 text-sm">No results returned for this query</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
