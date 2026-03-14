"use client";

import { useState, useRef } from "react";
import { Sparkles, Search, FileText, Loader2, AlertCircle } from "lucide-react";
import { semanticSearch } from "@/lib/api";
import type { SearchResultItem } from "@/lib/types";

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80
      ? "bg-emerald-900/60 text-emerald-300 border-emerald-700"
      : pct >= 60
      ? "bg-brand-900/60 text-brand-300 border-brand-700"
      : "bg-slate-800 text-slate-400 border-slate-700";
  return (
    <span className={`badge border text-xs font-mono px-2 py-0.5 ${color}`}>
      {pct}% match
    </span>
  );
}

function ResultCard({ result, index }: { result: SearchResultItem; index: number }) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="text-sm font-medium text-slate-300 truncate">
            {result.filename}
          </span>
          <span className="text-xs text-slate-600">·</span>
          <span className="text-xs text-slate-500">
            chunk {result.chunk_index + 1}
          </span>
          <span className="text-xs text-slate-600">·</span>
          <span className="text-xs text-slate-500">{result.token_count} tokens</span>
        </div>
        <ScoreBadge score={result.similarity_score} />
      </div>

      <p className="text-sm text-slate-300 leading-relaxed line-clamp-6">
        {result.text}
      </p>

      <div className="flex items-center gap-2 pt-1 border-t border-slate-800">
        <span className="text-xs text-slate-600 font-mono">#{index + 1}</span>
        <span className="text-xs text-slate-600">·</span>
        <span className="text-xs text-slate-600 font-mono truncate">
          doc: {result.document_id.slice(0, 8)}…
        </span>
      </div>
    </div>
  );
}

export default function SemanticSearchPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<SearchResultItem[] | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await semanticSearch(q, topK);
      setResults(data.results);
      setLastQuery(data.query);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-brand-900/40 border border-brand-800">
          <Sparkles className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Semantic Search</h1>
          <p className="text-sm text-slate-500">
            Find relevant document chunks using vector similarity
          </p>
        </div>
      </div>

      {/* Search box */}
      <div className="card mb-6">
        <div className="flex gap-3 items-start">
          <div className="flex-1">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. How do I configure SSO for CloudSuite?"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-brand-600 focus:border-brand-600"
            />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <label className="text-xs text-slate-500 whitespace-nowrap">Top</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-2.5 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-brand-600"
            >
              {[3, 5, 10, 20].map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              className="flex items-center gap-2 bg-brand-700 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Search
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 card border-red-800 bg-red-950/30 mb-6">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Searching embeddings…</span>
        </div>
      )}

      {/* Results */}
      {results !== null && !loading && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-slate-400">
              <span className="font-medium text-slate-200">{results.length}</span>{" "}
              result{results.length !== 1 ? "s" : ""} for{" "}
              <span className="font-medium text-brand-300">"{lastQuery}"</span>
            </p>
          </div>

          {results.length === 0 ? (
            <div className="card text-center py-12">
              <Sparkles className="w-8 h-8 text-slate-700 mx-auto mb-3" />
              <p className="text-sm text-slate-500">
                No matching chunks found. Try embedding a document first.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {results.map((r, i) => (
                <ResultCard key={r.chunk_id} result={r} index={i} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Empty state (no search yet) */}
      {results === null && !loading && !error && (
        <div className="card text-center py-12">
          <Sparkles className="w-8 h-8 text-slate-700 mx-auto mb-3" />
          <p className="text-slate-500 text-sm mb-1">
            Enter a query above to search your embedded documents
          </p>
          <p className="text-slate-600 text-xs">
            Documents must be ingested and embedded before they appear in results
          </p>
        </div>
      )}
    </div>
  );
}
