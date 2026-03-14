import type {
  AgentEvent,
  AgentRunDetail,
  AgentRunListResponse,
  AnalysisResult,
  Document,
  EmbedDocumentResponse,
  EntityListResponse,
  EvaluationMetrics,
  GraphRAGResponse,
  GraphResponse,
  GraphStats,
  GraphWriteResponse,
  HealthResponse,
  IssueListResponse,
  OntologyListResponse,
  OntologyVersionDetail,
  ProposalListResponse,
  RelationshipListResponse,
  SearchResponse,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

// ── Ingestion ─────────────────────────────────────────────────────────────────

export async function ingestText(
  rawText: string,
  filename?: string
): Promise<Document> {
  return apiFetch<Document>("/ingest", {
    method: "POST",
    body: JSON.stringify({
      source_type: "text",
      raw_text: rawText,
      metadata: filename ? { filename } : undefined,
    }),
  });
}

export async function ingestFile(file: File): Promise<Document> {
  const url = `${API_BASE}/ingest/upload`;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(url, { method: "POST", body: form });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<Document>;
}

export async function listDocuments(): Promise<Document[]> {
  return apiFetch<Document[]>("/ingest");
}

export async function deleteDocument(id: string): Promise<void> {
  const url = `${API_BASE}/ingest/${id}`;
  const res = await fetch(url, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
}

// ── Vector Memory ─────────────────────────────────────────────────────────────

export async function embedDocument(
  documentId: string
): Promise<EmbedDocumentResponse> {
  return apiFetch<EmbedDocumentResponse>(`/vector/embed-document/${documentId}`, {
    method: "POST",
  });
}

export async function semanticSearch(
  query: string,
  topK = 5
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  return apiFetch<SearchResponse>(`/vector/search?${params}`);
}

// ── Entities ──────────────────────────────────────────────────────────────────

export async function extractEntities(
  documentId: string
): Promise<EntityListResponse> {
  return apiFetch<EntityListResponse>(`/entities/extract/${documentId}`, {
    method: "POST",
  });
}

export async function listEntities(params?: {
  document_id?: string;
  entity_type?: string;
}): Promise<EntityListResponse> {
  const qs = new URLSearchParams();
  if (params?.document_id) qs.set("document_id", params.document_id);
  if (params?.entity_type) qs.set("entity_type", params.entity_type);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<EntityListResponse>(`/entities${query}`);
}

// ── Relationships ─────────────────────────────────────────────────────────────

export async function extractRelationships(
  documentId: string
): Promise<RelationshipListResponse> {
  return apiFetch<RelationshipListResponse>(`/relationships/extract/${documentId}`, {
    method: "POST",
  });
}

export async function listRelationships(params?: {
  document_id?: string;
  relationship_type?: string;
}): Promise<RelationshipListResponse> {
  const qs = new URLSearchParams();
  if (params?.document_id) qs.set("document_id", params.document_id);
  if (params?.relationship_type) qs.set("relationship_type", params.relationship_type);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<RelationshipListResponse>(`/relationships${query}`);
}

// ── Ontology ──────────────────────────────────────────────────────────────────

export async function generateOntology(params: {
  document_id?: string;
  domain_hint?: string;
}): Promise<OntologyVersionDetail> {
  return apiFetch<OntologyVersionDetail>("/ontology/generate", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function listOntologyVersions(params?: {
  document_id?: string;
}): Promise<OntologyListResponse> {
  const qs = new URLSearchParams();
  if (params?.document_id) qs.set("document_id", params.document_id);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<OntologyListResponse>(`/ontology${query}`);
}

export async function getOntologyVersion(
  versionId: string
): Promise<OntologyVersionDetail> {
  return apiFetch<OntologyVersionDetail>(`/ontology/${versionId}`);
}

// ── Graph ──────────────────────────────────────────────────────────────────────

export async function buildGraph(documentId: string): Promise<GraphWriteResponse> {
  return apiFetch<GraphWriteResponse>(`/graph/build/${documentId}`, { method: "POST" });
}

export async function getDocumentGraph(documentId: string): Promise<GraphResponse> {
  return apiFetch<GraphResponse>(`/graph/document/${documentId}`);
}

export async function getNeighborhood(entityId: string, depth = 2): Promise<GraphResponse> {
  return apiFetch<GraphResponse>(`/graph/neighborhood/${entityId}?depth=${depth}`);
}

export async function getGraphStats(): Promise<GraphStats> {
  return apiFetch<GraphStats>("/graph/stats");
}

// ── Agents ─────────────────────────────────────────────────────────────────────

export async function triggerPipeline(
  documentId: string,
  params?: { domain_hint?: string }
): Promise<{ run_id: string; status: string }> {
  return apiFetch(`/agents/run/${documentId}`, {
    method: "POST",
    body: JSON.stringify(params ?? {}),
  });
}

export async function listAgentRuns(params?: {
  document_id?: string;
  status?: string;
  limit?: number;
}): Promise<AgentRunListResponse> {
  const qs = new URLSearchParams();
  if (params?.document_id) qs.set("document_id", params.document_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<AgentRunListResponse>(`/agents/runs${query}`);
}

export async function getAgentRun(runId: string): Promise<AgentRunDetail> {
  return apiFetch<AgentRunDetail>(`/agents/runs/${runId}`);
}

/** Open an SSE stream for a running pipeline. Returns a cleanup function. */
export function streamAgentRun(
  runId: string,
  onEvent: (event: AgentEvent) => void
): () => void {
  const base =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
  const source = new EventSource(`${base}/agents/runs/${runId}/stream`);
  source.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data) as AgentEvent);
    } catch {
      // ignore malformed events
    }
  };
  source.onerror = () => source.close();
  return () => source.close();
}

// ── GraphRAG ───────────────────────────────────────────────────────────────────

export async function graphRagQuery(
  question: string,
  options?: { top_k?: number; max_hops?: number }
): Promise<GraphRAGResponse> {
  return apiFetch<GraphRAGResponse>("/query/graphrag", {
    method: "POST",
    body: JSON.stringify({ question, ...options }),
  });
}

// ── Learning / Knowledge Health ─────────────────────────────────────────────────

export async function triggerAnalysis(params?: {
  auto_correct?: boolean;
  confidence_threshold?: number;
}): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>("/learning/analyze", {
    method: "POST",
    body: JSON.stringify(params ?? {}),
  });
}

export async function getMetrics(threshold?: number): Promise<EvaluationMetrics> {
  const qs = threshold != null ? `?threshold=${threshold}` : "";
  return apiFetch<EvaluationMetrics>(`/learning/metrics${qs}`);
}

export async function listIssues(params?: {
  issue_type?: string;
  severity?: string;
  status?: string;
}): Promise<IssueListResponse> {
  const qs = new URLSearchParams();
  if (params?.issue_type) qs.set("issue_type", params.issue_type);
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.status) qs.set("status", params.status);
  return apiFetch<IssueListResponse>(`/learning/issues${qs.toString() ? "?" + qs : ""}`);
}

export async function listProposals(status?: string): Promise<ProposalListResponse> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<ProposalListResponse>(`/learning/proposals${qs}`);
}

export async function applyProposal(id: string): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/learning/proposals/${id}/apply`, { method: "POST" });
}

export async function dismissProposal(id: string): Promise<{ success: boolean }> {
  return apiFetch(`/learning/proposals/${id}/dismiss`, { method: "POST" });
}
