export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  environment: string;
  db_status: string;
  message: string | null;
}

export interface Document {
  id: string;
  source_type: string;
  filename: string | null;
  mime_type: string | null;
  size_kb: number | null;
  word_count: number | null;
  language: string | null;
  ingested_at: string;
  status: string;
}

export interface EmbedDocumentResponse {
  document_id: string;
  chunks_created: number;
  model_used: string;
  already_embedded: boolean;
}

export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  filename: string;
  text: string;
  similarity_score: number;
  chunk_index: number;
  token_count: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  top_k: number;
  results: SearchResultItem[];
}

export interface Entity {
  id: string;
  document_id: string;
  entity_type: string;
  name: string;
  attributes: Record<string, string>;
  evidence_chunk: string;
  confidence: number;
  created_at: string;
}

export interface EntityListResponse {
  entities: Entity[];
  total: number;
}

export interface Relationship {
  id: string;
  document_id: string;
  source_entity_id: string | null;
  target_entity_id: string | null;
  source_entity_name: string;
  target_entity_name: string;
  relationship_type: string;
  confidence: number;
  evidence_text: string;
  created_at: string;
}

export interface RelationshipListResponse {
  relationships: Relationship[];
  total: number;
}

// ── Ontology ──────────────────────────────────────────────────────────────────

export interface OntologyAttribute {
  name: string;
  type: string;
  description: string | null;
}

export interface OntologyClassDiscovered {
  name: string;
  description: string | null;
  attributes: OntologyAttribute[];
  synonyms: string[];
  parent_class: string | null;
}

export interface OntologyRelationshipDiscovered {
  source_class: string;
  predicate: string;
  target_class: string;
  description: string | null;
}

export interface OntologyContent {
  domain: string;
  classes: OntologyClassDiscovered[];
  relationships: OntologyRelationshipDiscovered[];
}

export interface OntologyVersionSummary {
  id: string;
  version: number;
  document_id: string | null;
  domain_hint: string | null;
  classes_count: number;
  relationships_count: number;
  model_used: string;
  created_at: string;
}

export interface OntologyVersionDetail extends OntologyVersionSummary {
  ontology: OntologyContent;
}

export interface OntologyListResponse {
  versions: OntologyVersionSummary[];
  total: number;
}

// ── Graph ──────────────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  labels: string[];
  properties: {
    name?: string;
    entity_type?: string;
    confidence?: number;
    attributes?: string;
  };
}

export interface GraphEdge {
  id: string;
  type: string;
  source_id: string;
  target_id: string;
  properties?: Record<string, unknown>;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface GraphWriteResponse {
  nodes_created: number;
  edges_created: number;
  nodes_updated: number;
  edges_updated: number;
}

export interface GraphStats {
  node_count: number;
  edge_count: number;
  label_distribution: Record<string, number>;
}

// ── GraphRAG ───────────────────────────────────────────────────────────────────

export interface ReasoningStep {
  step: string;
  description: string;
  result_count: number | null;
  detail: string | null;
}

export interface GraphRAGNode {
  id: string;
  name: string;
  entity_type: string;
  labels: string[];
  confidence: number | null;
}

export interface GraphRAGEdge {
  id: string;
  type: string;
  source_id: string;
  target_id: string;
  source_name: string | null;
  target_name: string | null;
}

export interface GraphRAGChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  text: string;
  similarity_score: number;
}

export interface GraphRAGResponse {
  question: string;
  answer: string;
  reasoning_trace: ReasoningStep[];
  ontology_classes: string[];
  graph_nodes: GraphRAGNode[];
  graph_edges: GraphRAGEdge[];
  document_chunks: GraphRAGChunk[];
  cypher_used: string | null;
  error: string | null;
}

// ── Agents ─────────────────────────────────────────────────────────────────────

export type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface StepResult {
  step_name: string;
  status: StepStatus;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  output_summary: string | null;
  error: string | null;
}

export interface AgentDecision {
  agent: string;
  message: string;
  timestamp: string;
}

export interface AgentRunSummary {
  id: string;
  document_id: string | null;
  document_name: string | null;
  status: string;
  current_step: string | null;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  steps_count: number;
  completed_steps_count: number;
}

export interface AgentRunDetail extends AgentRunSummary {
  steps: StepResult[];
  decisions: AgentDecision[];
}

export interface AgentRunListResponse {
  runs: AgentRunSummary[];
  total: number;
}

export interface AgentEvent {
  type:
    | "step_start"
    | "step_complete"
    | "step_failed"
    | "run_complete"
    | "run_failed"
    | "ping"
    | "done";
  step?: string;
  summary?: string;
  error?: string;
  timestamp?: string;
  status?: string;
}

// ── Learning / Knowledge Health ────────────────────────────────────────────────

export interface KnowledgeIssue {
  id: string;
  issue_type: string;
  severity: "error" | "warning" | "info";
  entity_id: string | null;
  relationship_id: string | null;
  document_id: string | null;
  description: string;
  detail: Record<string, unknown>;
  status: "open" | "resolved" | "dismissed";
  detected_at: string;
}

export interface OntologyProposal {
  id: string;
  proposal_type: "add_class" | "merge_class" | "add_relationship" | "rename_class";
  status: "pending" | "applied" | "dismissed";
  description: string;
  rationale: string;
  detail: Record<string, unknown>;
  proposed_at: string;
  applied_at: string | null;
}

export interface EvaluationMetrics {
  entity_count: number;
  relationship_count: number;
  entity_accuracy: number;
  relationship_accuracy: number;
  ontology_coverage: number;
  graph_completeness: number;
  low_confidence_entities: number;
  low_confidence_relationships: number;
  duplicate_entities: number;
  orphan_entities: number;
  unique_entity_types: number;
  ontology_class_count: number;
  neo4j_node_count: number;
  neo4j_edge_count: number;
}

export interface AnalysisResult {
  metrics: EvaluationMetrics;
  issues_detected: number;
  proposals_generated: number;
  auto_corrections_applied: number;
  duration_ms: number;
}

export interface IssueListResponse {
  issues: KnowledgeIssue[];
  total: number;
}

export interface ProposalListResponse {
  proposals: OntologyProposal[];
  total: number;
}
