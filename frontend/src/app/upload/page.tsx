"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Upload,
  FileText,
  Trash2,
  Loader2,
  X,
  CheckCircle,
  AlertCircle,
  Zap,
  Bot,
  ChevronDown,
} from "lucide-react";

import {
  ingestFile,
  ingestText,
  listDocuments,
  deleteDocument,
  embedDocument,
  triggerPipeline,
} from "@/lib/api";
import type { Document } from "@/lib/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(kb: number | null): string {
  if (kb == null) return "—";
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const ACCEPTED = ".pdf,.docx,.doc,.txt,.md";

type DocAction = "embed" | "pipeline" | "delete";
type ActionState = { id: string; action: DocAction } | null;

// ── Document row ──────────────────────────────────────────────────────────────

function DocRow({
  doc,
  busy,
  onEmbed,
  onPipeline,
  onDelete,
}: {
  doc: Document;
  busy: boolean;
  onEmbed: () => void;
  onPipeline: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <tr className="border-b border-slate-800 hover:bg-slate-800/30 transition-colors">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="text-slate-200 text-sm font-medium truncate max-w-xs">
            {doc.filename ?? doc.id}
          </span>
        </div>
      </td>
      <td className="px-4 py-3 text-slate-400 text-xs">
        {doc.source_type}
      </td>
      <td className="px-4 py-3 text-slate-400 text-xs">
        {doc.word_count != null ? `${doc.word_count.toLocaleString()} words` : "—"}
      </td>
      <td className="px-4 py-3 text-slate-400 text-xs">
        {formatBytes(doc.size_kb)}
      </td>
      <td className="px-4 py-3 text-slate-500 text-xs">
        {formatDate(doc.ingested_at)}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 justify-end">
          {busy ? (
            <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
          ) : (
            <>
              <button
                onClick={onEmbed}
                title="Create embeddings"
                className="p-1.5 rounded text-slate-500 hover:text-brand-400 hover:bg-slate-700 transition-colors"
              >
                <Zap className="w-4 h-4" />
              </button>
              <button
                onClick={onPipeline}
                title="Run full AI pipeline"
                className="p-1.5 rounded text-slate-500 hover:text-green-400 hover:bg-slate-700 transition-colors"
              >
                <Bot className="w-4 h-4" />
              </button>
              <button
                onClick={onDelete}
                title="Delete document"
                className="p-1.5 rounded text-slate-500 hover:text-red-400 hover:bg-slate-700 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type InputMode = "file" | "text";
type Toast = { id: number; type: "success" | "error"; message: string };

let toastId = 0;

export default function UploadPage() {
  const [mode, setMode] = useState<InputMode>("file");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);

  // File upload state
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Text paste state
  const [rawText, setRawText] = useState("");
  const [textFilename, setTextFilename] = useState("");
  const [ingestingText, setIngestingText] = useState(false);

  // Per-doc action state
  const [activeAction, setActiveAction] = useState<ActionState>(null);

  // Toasts
  const [toasts, setToasts] = useState<Toast[]>([]);

  function toast(type: "success" | "error", message: string) {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }

  async function refreshDocs() {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch {
      // silently ignore
    }
  }

  useEffect(() => {
    refreshDocs().finally(() => setLoadingDocs(false));
  }, []);

  // ── File upload ──────────────────────────────────────────────────────────────

  async function uploadFile(file: File) {
    setUploading(true);
    try {
      await ingestFile(file);
      toast("success", `"${file.name}" ingested successfully`);
      await refreshDocs();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
    e.target.value = "";
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragging(false), []);

  // ── Text ingest ──────────────────────────────────────────────────────────────

  async function handleIngestText() {
    if (!rawText.trim()) return;
    setIngestingText(true);
    try {
      const filename = textFilename.trim() || undefined;
      await ingestText(rawText, filename);
      toast("success", "Text document ingested successfully");
      setRawText("");
      setTextFilename("");
      await refreshDocs();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setIngestingText(false);
    }
  }

  // ── Per-doc actions ───────────────────────────────────────────────────────────

  async function handleEmbed(doc: Document) {
    setActiveAction({ id: doc.id, action: "embed" });
    try {
      const res = await embedDocument(doc.id);
      if (res.already_embedded) {
        toast("success", `Already embedded (${res.chunks_created} chunks)`);
      } else {
        toast("success", `Embedded ${res.chunks_created} chunks via ${res.model_used}`);
      }
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Embedding failed");
    } finally {
      setActiveAction(null);
    }
  }

  async function handlePipeline(doc: Document) {
    setActiveAction({ id: doc.id, action: "pipeline" });
    try {
      const res = await triggerPipeline(doc.id);
      toast("success", `Pipeline started (run ${res.run_id.slice(0, 8)}…)`);
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setActiveAction(null);
    }
  }

  async function handleDelete(doc: Document) {
    setActiveAction({ id: doc.id, action: "delete" });
    try {
      await deleteDocument(doc.id);
      toast("success", `Deleted "${doc.filename ?? doc.id}"`);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Delete failed");
    } finally {
      setActiveAction(null);
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <Upload className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Upload Documents</h1>
          <p className="text-slate-500 text-sm">Ingest PDFs, Word docs, and plain text into the knowledge graph</p>
        </div>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-1 mb-4 border-b border-slate-800">
        {(["file", "text"] as InputMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              mode === m
                ? "border-brand-500 text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            {m === "file" ? "File Upload" : "Paste Text"}
          </button>
        ))}
      </div>

      {/* ── FILE UPLOAD ──────────────────────────────────────────────────────── */}
      {mode === "file" && (
        <div
          className={`card flex flex-col items-center justify-center gap-4 py-16 border-2 border-dashed cursor-pointer transition-colors mb-6 ${
            dragging
              ? "border-brand-500 bg-brand-500/5"
              : "border-slate-700 hover:border-slate-500"
          }`}
          onClick={() => fileRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={handleFileInput}
          />
          {uploading ? (
            <>
              <Loader2 className="w-10 h-10 text-brand-400 animate-spin" />
              <p className="text-slate-300 font-medium">Uploading…</p>
            </>
          ) : (
            <>
              <Upload className={`w-10 h-10 ${dragging ? "text-brand-400" : "text-slate-500"}`} />
              <div className="text-center">
                <p className="text-slate-200 font-medium">
                  {dragging ? "Drop to upload" : "Drag & drop or click to choose"}
                </p>
                <p className="text-slate-500 text-sm mt-1">PDF, DOCX, TXT, Markdown</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── PASTE TEXT ───────────────────────────────────────────────────────── */}
      {mode === "text" && (
        <div className="card mb-6 flex flex-col gap-3">
          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">
              Filename (optional)
            </label>
            <input
              type="text"
              placeholder="e.g. quarterly_report.txt"
              value={textFilename}
              onChange={(e) => setTextFilename(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">
              Document text
            </label>
            <textarea
              rows={10}
              placeholder="Paste your document content here…"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-y font-mono"
            />
            <p className="text-xs text-slate-600 mt-1">
              {rawText.trim().split(/\s+/).filter(Boolean).length.toLocaleString()} words
            </p>
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleIngestText}
              disabled={!rawText.trim() || ingestingText}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {ingestingText ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {ingestingText ? "Ingesting…" : "Ingest Text"}
            </button>
          </div>
        </div>
      )}

      {/* ── DOCUMENT LIST ────────────────────────────────────────────────────── */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-brand-400" />
            <span className="text-sm font-medium text-slate-300">Ingested Documents</span>
            {documents.length > 0 && (
              <span className="bg-slate-700 rounded-full px-2 text-xs text-slate-400">
                {documents.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1"><Zap className="w-3 h-3" /> Embed</span>
            <span className="flex items-center gap-1"><Bot className="w-3 h-3" /> Pipeline</span>
            <span className="flex items-center gap-1"><Trash2 className="w-3 h-3" /> Delete</span>
          </div>
        </div>

        {loadingDocs ? (
          <div className="flex items-center justify-center py-16 gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
            <span className="text-slate-400 text-sm">Loading documents…</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <FileText className="w-8 h-8 text-slate-700" />
            <p className="text-slate-500 text-sm">No documents ingested yet</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-800/40">
                <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium">Filename</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-24">Source</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-28">Words</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-24">Size</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wide font-medium w-36">Ingested</th>
                <th className="px-4 py-3 w-28" />
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const busy =
                  activeAction?.id === doc.id;
                return (
                  <DocRow
                    key={doc.id}
                    doc={doc}
                    busy={busy}
                    onEmbed={() => handleEmbed(doc)}
                    onPipeline={() => handlePipeline(doc)}
                    onDelete={() => handleDelete(doc)}
                  />
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Toasts */}
      <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm border animate-in slide-in-from-right ${
              t.type === "success"
                ? "bg-green-900/90 border-green-700 text-green-200"
                : "bg-red-900/90 border-red-700 text-red-200"
            }`}
          >
            {t.type === "success" ? (
              <CheckCircle className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
