# Ontology Graph Studio — Technical Documentation

**Version 1.0 | Internal Platform — Developer & Architect Reference**

---

## 1. System Architecture Overview

```mermaid
graph LR
    subgraph Client ["Browser Client"]
        FE["Next.js 15\nApp Router\nReact 19 · TypeScript"]
        XY["ReactFlow\nGraph Visualiser"]
        SSE["SSE Client\nReal-time updates"]
    end

    subgraph Backend ["FastAPI Backend — port 8000"]
        ROUTER["Central API Router\n/api/*"]

        subgraph Pipeline ["AI Agent Pipeline (LangGraph)"]
            ENT["Entity Extractor\nClaude Haiku"]
            REL["Relation Extractor\nClaude Haiku"]
            ONT["Ontology Discovery\nClaude Sonnet"]
            GW["Graph Writer"]
            VEC["Vector Embedder\nOpenAI"]
        end

        GRAPHRAG["GraphRAG Service\nHaiku + Sonnet"]
        LEARN["Knowledge Evolution Engine"]
        EMBED["Embedding Service\npgvector"]
    end

    subgraph Data ["Data Layer"]
        PG[("PostgreSQL 16\n+ pgvector\nport 5432")]
        NEO[("Neo4j\nport 7474/7687")]
    end

    subgraph AI ["External AI"]
        CLAUDE["Anthropic Claude\nHaiku · Sonnet"]
        OPENAI["OpenAI\ntext-embedding-ada-002"]
    end

    FE --> ROUTER
    XY --> ROUTER
    SSE --> ROUTER
    ROUTER --> Pipeline
    ROUTER --> GRAPHRAG
    ROUTER --> LEARN
    Pipeline --> PG
    Pipeline --> NEO
    GRAPHRAG --> PG
    GRAPHRAG --> NEO
    LEARN --> PG
    LEARN --> NEO
    ENT --> CLAUDE
    REL --> CLAUDE
    ONT --> CLAUDE
    GRAPHRAG --> CLAUDE
    LEARN --> CLAUDE
    VEC --> OPENAI
    EMBED --> OPENAI
```

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend framework | Next.js (App Router) | 15.1.0 |
| Frontend language | TypeScript | 5.7 |
| Frontend styling | Tailwind CSS | 3.4 |
| Graph visualisation | @xyflow/react | 12.x |
| Backend framework | FastAPI | latest |
| Backend language | Python | 3.11 |
| ORM | SQLAlchemy 2 (async) | 2.x |
| AI orchestration | LangGraph (StateGraph) | latest |
| Relational DB | PostgreSQL + pgvector | 16 |
| Graph DB | Neo4j | 5.x |
| Primary AI models | Anthropic Claude Haiku 4.5 / Sonnet 4.6 | — |
| Embedding model | OpenAI text-embedding-ada-002 | — |
| Container runtime | Docker + Docker Compose | — |

---

## 2. Backend Services

The backend is a single FastAPI application (`backend/app/main.py`) that mounts all domain routers under `/api`. Each domain lives in its own module under `backend/app/`.

### 2.1 Ingestion Service

**Location:** `backend/app/ingestion/`
**Router:** `backend/app/api/routes/ingestion.py`
**Prefix:** `/api/ingest`

The ingestion service reads raw text from uploaded files (TXT, PDF, DOCX) and stores `Document` rows in PostgreSQL. An abstract `BaseIngester` interface allows multiple ingesters by source type.

**Key class:**
```python
class BaseIngester:
    async def can_handle(source: str) -> bool
    async def ingest(source: str, metadata: dict | None) -> IngestedDocument
```

**IngestedDocument fields:** `id`, `source_type`, `raw_text`, `filename`, `mime_type`, `size_kb`, `language`, `metadata`, `ingested_at`

---

### 2.2 Entity Extraction Service

**Location:** `backend/app/extraction/entity_extractor.py`
**Router:** `backend/app/api/routes/entities.py`
**Prefix:** `/api/entities`

Reads a document in overlapping text chunks (chunk_size=600, overlap=50 tokens) and sends each chunk to Claude Haiku for entity extraction. Merges deduplicated results across chunks. Stores `ExtractedEntity` rows in PostgreSQL.

**Supported entity types (frozenset — cannot be extended at runtime):**

```python
ENTITY_TYPES = frozenset({
    "Company", "Person", "Product", "Contract",
    "Location", "Technology", "Policy", "Regulation"
})
```

**Key class:**
```python
class EntityExtractionAgent:
    def __init__(self, chunk_size: int = 600, overlap: int = 50)
    async def extract(document_id: str, text: str) -> ExtractionResult
```

---

### 2.3 Relationship Extraction Service

**Location:** `backend/app/extraction/relation_extractor.py`
**Router:** `backend/app/api/routes/relationships.py`
**Prefix:** `/api/relationships`

After entities are extracted, reads entity pairs in context chunks (chunk_size=800, overlap=100) and identifies typed relationships between them using Claude Haiku. Stores `ExtractedRelationship` rows in PostgreSQL.

**Supported relationship types (frozenset):**

```python
RELATIONSHIP_TYPES = frozenset({
    "WORKS_FOR", "OWNS", "USES", "BELONGS_TO", "RENEWS",
    "EXPIRES_ON", "LOCATED_IN", "DEPENDS_ON", "SELLS_TO", "GOVERNED_BY"
})
```

**Key class:**
```python
class RelationExtractor:
    async def extract(document_id: str, text: str) -> ExtractionResult
    async def extract_from_entities(
        document_id: str, text: str, entities: list[Entity]
    ) -> ExtractionResult
```

---

### 2.4 Ontology Discovery Service

**Location:** `backend/app/ontology/discovery_agent.py`
**Router:** `backend/app/api/routes/ontology.py`
**Prefix:** `/api/ontology`

Uses Claude Sonnet to analyse extracted entities and relationships and infer a domain-specific ontology: class names, descriptions, attributes, synonyms, parent classes, and relationship predicates. Each generation creates a versioned `OntologyVersion` row stored as JSON.

An in-memory `OntologyManager` singleton maintains the active ontology. It is seeded with 5 default classes on startup and can be extended via `create_class()`.

**Key classes:**
```python
class OntologyDiscoveryAgent:
    async def discover(
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship],
        domain_hint: str | None
    ) -> dict

class OntologyManager:
    def list_classes() -> list[OntologyClass]
    def create_class(name: str, description: str) -> OntologyClass  # raises ValueError if exists
```

---

### 2.5 Graph Builder / Reader

**Location:** `backend/app/graph/`
**Router:** `backend/app/api/routes/graph.py`
**Prefix:** `/api/graph`

Writes extracted entities and relationships to Neo4j using `MERGE` semantics (idempotent). Entities become labelled nodes; relationships become typed edges. The reader service traverses the graph for API responses.

**Key classes:**
```python
class GraphBuilderService:
    async def build(
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship]
    ) -> dict  # {nodes_created, nodes_updated, edges_created, edges_updated}

class GraphReader:
    async def get_document_graph(document_id: str) -> dict
    async def get_neighborhood(pg_id: str, depth: int = 2) -> dict
    async def get_stats() -> dict  # raises RuntimeError if Neo4j offline

class Neo4jClient:
    async def run(cypher: str, parameters: dict | None) -> list[dict]
    async def health_check() -> bool
```

**Node property schema (in Neo4j):**

| Property | Type | Description |
|----------|------|-------------|
| `pg_id` | String | PostgreSQL UUID — primary cross-reference key |
| `name` | String | Entity name as extracted |
| `entity_type` | String | One of the ENTITY_TYPES values |
| `confidence` | Float | 0.0 – 1.0 |
| `attributes` | String (JSON) | Additional key-value attributes |

**Edge property schema (in Neo4j):**

| Property | Type | Description |
|----------|------|-------------|
| `pg_id` | String | PostgreSQL UUID |
| `type` | String | Relationship type (e.g., USES, DEPENDS_ON) |
| `confidence` | Float | 0.0 – 1.0 |
| `evidence` | String | Source text supporting this relationship |

---

### 2.6 Vector Embedding Service

**Location:** `backend/app/vector_memory/embedding_service.py`
**Router:** `backend/app/api/routes/vector_memory.py`
**Prefix:** `/api/vector`

Chunks document text and embeds each chunk using OpenAI's embedding model. Stores `ChunkEmbedding` rows with `embedding vector(1536)` in PostgreSQL via pgvector. Supports cosine-similarity nearest-neighbour search.

**Key class:**
```python
class VectorEmbeddingService:
    async def embed_document(document_id: str, db: AsyncSession) -> EmbedResult
    async def semantic_search(query: str, top_k: int, db: AsyncSession) -> list[SearchResult]
```

**Chunk parameters:** chunk_size ≈ 512 tokens, stored with `chunk_index`, `token_count`, and `metadata_json`.

---

### 2.7 GraphRAG Service

**Location:** `backend/app/graphrag/service.py`
**Router:** `backend/app/api/routes/graphrag.py`
**Prefix:** `/api/query`

Implements a 4-step retrieval-augmented generation pipeline combining ontology reasoning, graph traversal, and vector search.

**Pipeline steps:**

```
Step 1: Ontology Class Identification
  → Claude Haiku: given the question and all known class names, return relevant classes

Step 2: Graph Traversal
  → Neo4j: MATCH nodes WHERE entity_type IN [relevant_classes], retrieve ≤60 nodes + ≤80 edges
  → Fallback: if no seed nodes found, return all nodes up to limit

Step 3: Vector Retrieval
  → pgvector: top-K semantically similar document chunks

Step 4: Answer Synthesis
  → Claude Sonnet: grounded answer from graph nodes + edges + document passages
```

**Key class:**
```python
class GraphRAGService:
    async def query(
        question: str, top_k: int, max_hops: int, db: AsyncSession
    ) -> GraphRAGResponse
```

**Configuration constants:**
- `_MAX_NODES = 60` — maximum graph nodes per query
- `_MAX_EDGES = 80` — maximum graph edges per query

---

### 2.8 AI Agent Pipeline

**Location:** `backend/app/agents/pipeline.py`
**Router:** `backend/app/api/routes/agents.py`
**Prefix:** `/api/agents`

A LangGraph `StateGraph` orchestrating all five pipeline stages sequentially. Runs asynchronously in a background task. Progress is tracked in the `AgentRun` PostgreSQL table and streamed to clients via SSE.

**Pipeline state:**
```python
class PipelineState(TypedDict):
    run_id: str
    document_id: str
    document_text: str
    domain_hint: str | None
    entity_ids: list[str]
    relationship_ids: list[str]
    ontology_version_id: str | None
    graph_stats: dict
    embed_result: dict
    errors: list[str]
    decisions: list[dict]
    completed_steps: list[str]
```

**Pipeline nodes (executed in order):**
1. `entity_extraction_node`
2. `relationship_discovery_node`
3. `ontology_builder_node`
4. `graph_update_node`
5. `vector_memory_node`

**Entry point:**
```python
async def run_pipeline(run_id: str, document_id: str, domain_hint: str | None) -> None
```

**AgentRun status values:** `pending` → `running` → `completed` / `failed`

---

### 2.9 Knowledge Evolution Engine

**Location:** `backend/app/learning/engine.py`
**Router:** `backend/app/api/routes/learning.py`
**Prefix:** `/api/learning`

A continuous quality assurance service that analyses the knowledge graph for issues, generates ontology improvement proposals via Claude Haiku, and can auto-correct obvious inconsistencies.

**Key class:**
```python
class KnowledgeEvolutionEngine:
    async def compute_metrics(db, threshold=0.5) -> EvaluationMetrics
    async def detect_issues(db, threshold=0.5) -> list[KnowledgeIssue]
    async def generate_proposals(db) -> list[OntologyProposal]
    async def auto_correct(db) -> int  # returns correction count
    async def apply_proposal(proposal_id, db) -> tuple[bool, str]
    async def dismiss_proposal(proposal_id, db) -> bool
    async def analyze(db, auto_correct=False, threshold=0.5) -> AnalysisResult
```

**Issue detection logic:**

| Issue Type | Severity | Detection Rule |
|------------|----------|----------------|
| `low_confidence_entity` | warning | `confidence < threshold` |
| `low_confidence_relationship` | warning | `confidence < threshold` |
| `duplicate_entity` | error | Same name + document_id, count > 1 |
| `orphan_entity` | info | Entity not referenced in any relationship |
| `unknown_entity_type` | warning | `entity_type.lower()` not in ENTITY_TYPES |
| `sparse_relationships` | info | Document with >5 entities but <2 relationships |

**Orphan detection uses UNION subquery to avoid PostgreSQL parameter limits:**
```python
ref_subq = (
    select(ExtractedRelationship.source_entity_id.label("eid"))
    .union(select(ExtractedRelationship.target_entity_id.label("eid")))
).subquery()
```

---

## 3. Complete API Reference

Base URL: `http://localhost:8000/api`

All requests use JSON (`Content-Type: application/json`). Authentication is not currently implemented (internal network deployment). Responses follow `{success: bool, ...payload}` structure.

---

### Health

#### `GET /health`

Returns service health status.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-03-13T17:31:56Z",
  "environment": "development",
  "db_status": "configured",
  "message": "Ontology Graph Studio backend is running"
}
```

```bash
curl http://localhost:8000/api/health
```

---

### Ingestion

#### `POST /ingest/upload`

Upload a document file (TXT, PDF, DOCX).

**Request:** `multipart/form-data` with `file` field
**Response:** `IngestedDocumentResponse`

```bash
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@/path/to/document.pdf"
```

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source_type": "file",
  "filename": "document.pdf",
  "mime_type": "application/pdf",
  "size_kb": 142.3,
  "word_count": 4821,
  "language": "en",
  "ingested_at": "2026-03-13T10:00:00Z",
  "status": "ingested"
}
```

#### `POST /ingest`

Ingest raw text.

**Request:**
```json
{
  "source_type": "text",
  "raw_text": "Full document text here...",
  "metadata": {"author": "Jane Smith"}
}
```

#### `GET /ingest`

List all ingested documents. Returns array of `IngestedDocumentResponse`.

```bash
curl http://localhost:8000/api/ingest
```

#### `GET /ingest/{document_id}`

Get a single document by ID.

#### `DELETE /ingest/{document_id}`

Delete a document and all cascading data (entities, relationships, embeddings).

---

### Entity Extraction

#### `POST /entities/extract/{document_id}`

Run AI entity extraction on a document. Requires document to be ingested first.

**Request:**
```json
{}
```

**Response:**
```json
{
  "entities": [
    {
      "id": "...",
      "document_id": "...",
      "entity_type": "Company",
      "name": "Acme Corporation",
      "attributes": {"industry": "Software"},
      "evidence_chunk": "Acme Corporation signed a 3-year agreement...",
      "confidence": 0.94,
      "created_at": "2026-03-13T10:05:00Z"
    }
  ],
  "total": 47
}
```

```bash
curl -X POST http://localhost:8000/api/entities/extract/{document_id}
```

#### `GET /entities`

List extracted entities. Query parameters: `document_id`, `entity_type`, `limit` (default 100), `offset` (default 0).

```bash
curl "http://localhost:8000/api/entities?entity_type=Company&limit=20"
```

---

### Relationship Extraction

#### `POST /relationships/extract/{document_id}`

Run AI relationship extraction. Entities must exist for the document first.

**Response:**
```json
{
  "relationships": [
    {
      "id": "...",
      "source_entity_name": "Acme Corporation",
      "target_entity_name": "CloudStack",
      "relationship_type": "USES",
      "confidence": 0.87,
      "evidence_text": "Acme Corporation uses CloudStack for all production workloads"
    }
  ],
  "total": 31
}
```

#### `GET /relationships`

List extracted relationships. Query parameters: `document_id`, `relationship_type`, `limit`, `offset`.

---

### Ontology

#### `POST /ontology/generate`

Run AI ontology discovery on extracted entities and relationships.

**Request:**
```json
{
  "document_id": "optional-document-uuid",
  "domain_hint": "finance"
}
```

**Response:** `OntologyVersionDetail` — full ontology content with classes and relationships.

```bash
curl -X POST http://localhost:8000/api/ontology/generate \
  -H "Content-Type: application/json" \
  -d '{"domain_hint": "technology infrastructure"}'
```

#### `GET /ontology/classes`

List active ontology classes from in-memory manager.

#### `POST /ontology/classes`

Add a new class to the active ontology.

**Request:**
```json
{
  "name": "Vendor",
  "description": "An external supplier of goods or services",
  "parent_class": "Organization",
  "properties": []
}
```

#### `GET /ontology`

List all ontology versions. Query parameter: `document_id` to filter.

#### `GET /ontology/{version_id}`

Get full ontology version including all classes, relationships, and raw JSON.

---

### Graph

#### `POST /graph/build/{document_id}`

Write extracted entities and relationships from PostgreSQL into Neo4j. Idempotent (uses MERGE).

**Response:**
```json
{
  "nodes_created": 12,
  "nodes_updated": 3,
  "edges_created": 18,
  "edges_updated": 0
}
```

```bash
curl -X POST http://localhost:8000/api/graph/build/{document_id}
```

#### `GET /graph/document/{document_id}`

Get all nodes and edges for a document.

**Response:** `GraphResponse` — `{nodes[], edges[], node_count, edge_count}`

#### `GET /graph/neighborhood/{entity_id}`

Get the N-hop neighborhood of an entity node. Query parameter: `depth` (default 2).

```bash
curl "http://localhost:8000/api/graph/neighborhood/{pg_id}?depth=2"
```

#### `GET /graph/stats`

Get overall graph statistics (node count, edge count, label distribution). Requires Neo4j to be running.

---

### Query

#### `POST /query`

Execute a natural language query. Translates to Cypher and executes against Neo4j.

**Request:**
```json
{
  "query": "Which companies use AWS?",
  "document_id": "optional-filter-uuid",
  "mode": "natural_language"
}
```

**Response:**
```json
{
  "query": "Which companies use AWS?",
  "cypher": "MATCH (c {entity_type: 'Company'})-[:USES]->(t {name: 'AWS'}) RETURN c.name",
  "results": [...],
  "answer": "Based on the knowledge graph, the following companies use AWS: ...",
  "sources": [...],
  "error": null
}
```

---

### GraphRAG

#### `POST /query/graphrag`

Full Graph-RAG retrieval: ontology class matching → graph traversal → vector search → answer synthesis.

**Request:**
```json
{
  "question": "Which companies depend on AWS?",
  "top_k": 5,
  "max_hops": 2
}
```

**Response:**
```json
{
  "question": "Which companies depend on AWS?",
  "answer": "Based on the knowledge graph and document corpus, the following companies have a dependency on AWS...",
  "reasoning_trace": [
    {"step": "ontology_matching", "description": "Identified relevant ontology classes", "result_count": 2, "detail": "Matched: Company, Technology"},
    {"step": "graph_traversal", "description": "Traversed Neo4j", "result_count": 34, "detail": "34 nodes, 28 edges"},
    {"step": "vector_retrieval", "description": "Retrieved document passages", "result_count": 5, "detail": "Top-5 chunks; best similarity: 0.891"},
    {"step": "synthesis", "description": "Synthesised answer", "result_count": null, "detail": "Used 34 nodes, 28 edges, 5 chunks"}
  ],
  "ontology_classes": ["Company", "Technology"],
  "graph_nodes": [...],
  "graph_edges": [...],
  "document_chunks": [...],
  "cypher_used": "MATCH (n) WHERE toLower(n.entity_type) IN ['company', 'technology']...",
  "error": null
}
```

```bash
curl -X POST http://localhost:8000/api/query/graphrag \
  -H "Content-Type: application/json" \
  -d '{"question": "Which companies depend on AWS?", "top_k": 5, "max_hops": 2}'
```

---

### Vector / Semantic Search

#### `POST /vector/embed-document/{document_id}`

Chunk a document and store OpenAI embeddings in pgvector. Idempotent.

**Response:**
```json
{
  "document_id": "...",
  "chunks_created": 24,
  "model_used": "text-embedding-ada-002",
  "already_embedded": false
}
```

#### `GET /vector/search`

Semantic similarity search. Query parameters: `q` (query string), `top_k` (default 5).

```bash
curl "http://localhost:8000/api/vector/search?q=payment+terms+and+late+fees&top_k=10"
```

**Response:**
```json
{
  "query": "payment terms and late fees",
  "top_k": 10,
  "results": [
    {
      "chunk_id": "...",
      "document_id": "...",
      "filename": "vendor_contract.pdf",
      "text": "Payment is due within 30 days. Late fees of 1.5% per month apply...",
      "similarity_score": 0.912,
      "chunk_index": 7,
      "token_count": 498,
      "metadata": {}
    }
  ]
}
```

---

### Agents

#### `POST /agents/run/{document_id}`

Trigger the full AI pipeline for a document. Returns immediately with `run_id`.

**Request:**
```json
{
  "domain_hint": "finance"
}
```

**Response (202 Accepted):**
```json
{
  "run_id": "...",
  "status": "pending"
}
```

```bash
curl -X POST http://localhost:8000/api/agents/run/{document_id} \
  -H "Content-Type: application/json" \
  -d '{"domain_hint": "finance"}'
```

#### `GET /agents/runs`

List all pipeline runs. Query parameters: `document_id`, `status`, `limit` (default 30), `offset`.

#### `GET /agents/runs/{run_id}`

Get full detail for a pipeline run including all step results and agent decisions.

**Response fields:** `id`, `document_id`, `status`, `current_step`, `started_at`, `completed_at`, `error_message`, `steps[]`, `decisions[]`

#### `GET /agents/runs/{run_id}/stream`

SSE event stream for real-time pipeline progress. Returns `text/event-stream`.

```bash
curl -N http://localhost:8000/api/agents/runs/{run_id}/stream
```

Each event: `data: {"type": "step_complete", "step": "entity_extraction", "status": "completed"}`

---

### Learning (Knowledge Evolution)

#### `POST /learning/analyze`

Run the full Knowledge Evolution Engine: detect issues, generate proposals, optionally auto-correct, compute metrics.

**Request:**
```json
{
  "auto_correct": false,
  "confidence_threshold": 0.5
}
```

**Response:**
```json
{
  "metrics": {
    "entity_count": 115,
    "relationship_count": 93,
    "entity_accuracy": 0.96,
    "relationship_accuracy": 0.89,
    "ontology_coverage": 0.72,
    "graph_completeness": 0.81,
    "low_confidence_entities": 4,
    "low_confidence_relationships": 7,
    "duplicate_entities": 3,
    "orphan_entities": 12,
    "unique_entity_types": 5,
    "ontology_class_count": 6,
    "neo4j_node_count": 115,
    "neo4j_edge_count": 93
  },
  "issues_detected": 24,
  "proposals_generated": 5,
  "auto_corrections_applied": 0,
  "duration_ms": 312
}
```

```bash
curl -X POST http://localhost:8000/api/learning/analyze \
  -H "Content-Type: application/json" \
  -d '{"auto_correct": false, "confidence_threshold": 0.5}'
```

#### `GET /learning/metrics`

Compute metrics without running full analysis. Query parameter: `threshold` (default 0.5).

#### `GET /learning/issues`

List detected knowledge issues. Query parameters: `issue_type`, `severity`, `status` (default `open`).

```bash
curl "http://localhost:8000/api/learning/issues?severity=error"
```

#### `GET /learning/proposals`

List ontology proposals. Query parameter: `status` (default `pending`).

#### `POST /learning/proposals/{proposal_id}/apply`

Apply a pending ontology proposal.

**Response:**
```json
{"success": true, "message": "Added ontology class 'Vendor'"}
```

#### `POST /learning/proposals/{proposal_id}/dismiss`

Dismiss a pending proposal.

---

## 4. API Access Guide

### Base URL and Content Type

```
Base URL: http://localhost:8000/api
Content-Type: application/json (for POST/PUT)
Accept: application/json
```

### Authentication

The platform does not currently implement authentication — it is designed for internal network deployment. API Gateway or reverse proxy authentication (e.g., Nginx + OAuth2 proxy) should be added for production deployments exposed beyond a private network.

### Error Response Format

```json
{
  "detail": "Document not found: 550e8400-...",
  "status_code": 404
}
```

Standard HTTP status codes apply:
- `200 OK` — Success
- `202 Accepted` — Background task started (agent pipeline)
- `400 Bad Request` — Invalid input
- `404 Not Found` — Resource not found
- `500 Internal Server Error` — Unhandled server error
- `501 Not Implemented` — Route exists but module not yet built

### Interactive API Docs

FastAPI generates OpenAPI documentation automatically:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Rate Limits

No rate limits are enforced. AI calls (Claude, OpenAI) are subject to external provider rate limits. For high-volume processing, implement a queue (e.g., Celery + Redis) between the API and the AI pipeline.

---

## 5. Neo4j Graph Explorer

### Connection Details

| Parameter | Value |
|-----------|-------|
| Bolt URI | `bolt://localhost:7687` |
| HTTP Browser | http://localhost:7474 |
| Default username | `neo4j` |
| Default password | Set in `docker-compose.yml` env `NEO4J_AUTH` |

### Connecting via Browser

1. Open http://localhost:7474
2. Select **Bolt** as the connection type
3. Enter `bolt://localhost:7687`
4. Log in with the credentials from `docker-compose.yml`
5. The browser opens to the Neo4j Graph Explorer

### Connecting Programmatically

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "your-password")
)

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) AS total")
    print(result.single()["total"])
```

---

### Sample Cypher Queries

#### View all nodes
```cypher
MATCH (n) RETURN n LIMIT 50
```

#### Count nodes by entity type
```cypher
MATCH (n)
WHERE n.entity_type IS NOT NULL
RETURN n.entity_type AS type, count(n) AS count
ORDER BY count DESC
```

#### Find all companies and what they use
```cypher
MATCH (c)-[:USES]->(t)
WHERE c.entity_type = 'Company'
RETURN c.name AS company, t.name AS uses, t.entity_type AS target_type
ORDER BY c.name
```

#### Find all contract expiry relationships
```cypher
MATCH (c {entity_type: 'Contract'})-[:EXPIRES_ON]->(d)
RETURN c.name AS contract, d.name AS expiry_date
ORDER BY d.name
```

#### Traverse 2-hop neighborhood around a specific entity
```cypher
MATCH path = (n {name: 'AWS'})-[*1..2]-(neighbor)
RETURN path
LIMIT 100
```

#### Find all entities connected to a regulation
```cypher
MATCH (e)-[:GOVERNED_BY]->(r {entity_type: 'Regulation'})
RETURN e.name AS entity, e.entity_type AS type, r.name AS regulation
ORDER BY r.name, e.name
```

#### Find entities that appear in multiple documents
```cypher
MATCH (n)
WHERE n.entity_type IS NOT NULL
WITH n.name AS name, count(DISTINCT n.pg_id) AS occurrences
WHERE occurrences > 1
RETURN name, occurrences
ORDER BY occurrences DESC
```

#### Find low-confidence relationships
```cypher
MATCH (a)-[r]->(b)
WHERE r.confidence < 0.5
RETURN a.name AS source, type(r) AS relationship, b.name AS target, r.confidence
ORDER BY r.confidence ASC
LIMIT 50
```

#### Delete all nodes and edges (reset graph)
```cypher
MATCH (n) DETACH DELETE n
```

---

### Exploring the Graph Visually

In the Neo4j Browser:
1. Run a query (e.g., `MATCH (n) RETURN n LIMIT 50`)
2. Click the **Graph** tab in the result panel (not Table)
3. Nodes appear as circles — double-click any node to expand its relationships
4. Use the legend (bottom-left) to filter by label
5. Right-click a node to access "Expand" and "Hide" options
6. Use the style panel (top-right) to colour-code by property values

---

## 6. Data Model

### PostgreSQL Tables

#### `documents`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| filename | VARCHAR | Original filename |
| mime_type | VARCHAR | e.g., `application/pdf` |
| raw_text | TEXT | Full extracted text content |
| word_count | INTEGER | Word count of raw text |
| language | VARCHAR | ISO 639-1 language code |
| created_at | TIMESTAMPTZ | Ingestion timestamp |

#### `extracted_entities`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| document_id | VARCHAR (FK→documents) | Source document |
| entity_type | VARCHAR | One of ENTITY_TYPES |
| name | VARCHAR | Extracted entity name |
| attributes_json | TEXT | JSON key-value attributes |
| evidence_chunk | TEXT | Source text supporting the extraction |
| confidence | FLOAT | 0.0 – 1.0 |
| created_at | TIMESTAMPTZ | — |

#### `extracted_relationships`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| document_id | VARCHAR (FK→documents) | Source document |
| source_entity_id | VARCHAR | Source entity UUID |
| target_entity_id | VARCHAR | Target entity UUID |
| source_entity_name | VARCHAR | Denormalised source name |
| target_entity_name | VARCHAR | Denormalised target name |
| relationship_type | VARCHAR | One of RELATIONSHIP_TYPES |
| confidence | FLOAT | 0.0 – 1.0 |
| evidence_text | TEXT | Source text |
| created_at | TIMESTAMPTZ | — |

#### `chunk_embeddings`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| document_id | VARCHAR (FK→documents) | Source document |
| chunk_index | INTEGER | Chunk sequence number |
| text | TEXT | Raw chunk text |
| embedding | vector(1536) | OpenAI embedding (pgvector) |
| token_count | INTEGER | Token count of chunk |
| metadata_json | TEXT | JSON chunk metadata |
| created_at | TIMESTAMPTZ | — |

#### `ontology_versions`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| version | INTEGER | Monotonically increasing version number |
| document_id | VARCHAR (FK, nullable) | Source document (if document-scoped) |
| domain_hint | VARCHAR | User-provided domain label |
| ontology_json | TEXT | Full JSON of classes + relationships |
| classes_count | INTEGER | Number of classes in this version |
| relationships_count | INTEGER | Number of relationship predicates |
| model_used | VARCHAR | Claude model that generated this version |
| created_at | TIMESTAMPTZ | — |

#### `agent_runs`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| document_id | VARCHAR (FK, nullable) | Source document |
| status | VARCHAR | pending / running / completed / failed |
| current_step | VARCHAR | Currently executing pipeline stage |
| steps_json | TEXT | JSON array of StepResult objects |
| decisions_json | TEXT | JSON array of AgentDecision objects |
| started_at | TIMESTAMPTZ | — |
| completed_at | TIMESTAMPTZ | — |
| error_message | TEXT | Last error if status=failed |

#### `knowledge_issues`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| issue_type | VARCHAR | See issue type table above |
| severity | VARCHAR | error / warning / info |
| entity_id | VARCHAR | Affected entity UUID (nullable) |
| relationship_id | VARCHAR | Affected relationship UUID (nullable) |
| document_id | VARCHAR (FK, nullable) | Source document |
| description | TEXT | Human-readable description |
| detail_json | TEXT | JSON structured detail |
| status | VARCHAR | open / resolved |
| detected_at | TIMESTAMPTZ | — |

#### `ontology_proposals`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (UUID) | Primary key |
| proposal_type | VARCHAR | add_class / merge_class / rename_class / add_relationship |
| status | VARCHAR | pending / applied / dismissed |
| description | TEXT | What the proposal does |
| rationale | TEXT | Why the proposal was generated |
| detail_json | TEXT | JSON with subject, target, description fields |
| proposed_at | TIMESTAMPTZ | — |
| applied_at | TIMESTAMPTZ | Set when applied |

### Neo4j Graph Model

#### Node Labels

All entity nodes carry the label `Entity` plus a dynamic label matching their `entity_type` value.

**Node properties:**
```
(Entity {
  pg_id: "uuid-from-postgres",
  name: "Acme Corporation",
  entity_type: "Company",
  confidence: 0.94,
  attributes: "{\"industry\": \"Software\"}"
})
```

#### Relationship Types

```
(src)-[:WORKS_FOR]->(tgt)
(src)-[:OWNS]->(tgt)
(src)-[:USES]->(tgt)
(src)-[:BELONGS_TO]->(tgt)
(src)-[:RENEWS]->(tgt)
(src)-[:EXPIRES_ON]->(tgt)
(src)-[:LOCATED_IN]->(tgt)
(src)-[:DEPENDS_ON]->(tgt)
(src)-[:SELLS_TO]->(tgt)
(src)-[:GOVERNED_BY]->(tgt)
```

**Edge properties:**
```
-[:USES {
  pg_id: "uuid",
  confidence: 0.87,
  evidence: "Acme uses AWS for all production workloads"
}]->
```

---

## 7. Deployment Architecture

### Docker Compose Services

**File:** `docker-compose.yml`

| Service | Image | Port | Role |
|---------|-------|------|------|
| `postgres` | postgres:16 + pgvector | 5432 | Relational store + vector index |
| `neo4j` | neo4j:5 | 7474 (HTTP), 7687 (Bolt) | Graph database |
| `backend` | Custom (Python 3.11) | 8000 | FastAPI application server |
| `frontend` | Custom (Node 20) | 3000 | Next.js dev server |

### Environment Variables

**Backend (`.env`):**

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kgapp
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# App
APP_ENV=development
LOG_LEVEL=DEBUG
```

**Frontend (`.env.local`):**

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Environment Tiers

| Environment | Backend URL | Frontend URL | DB | Notes |
|-------------|-------------|-------------|----|----|
| **Dev** | localhost:8000 | localhost:3000 | Docker Compose | Hot reload enabled, DEBUG logging |
| **QA** | qa.internal:8000 | qa.internal:3000 | Dedicated PG + Neo4j | Standard logging, no hot reload |
| **Production** | api.internal:8000 | app.internal:3000 | Managed PG + Neo4j AuraDB | INFO logging, HTTPS, auth required |

### Starting Locally

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker compose up --build

# Or run without Docker (requires local PG + Neo4j)
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

cd frontend
npm run dev
```

### Database Migrations

Tables are created automatically on startup via SQLAlchemy `create_all`. For production, replace with Alembic migrations:

```bash
cd backend
alembic init alembic
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## 8. Observability and Monitoring

### Structured Logging

The backend uses a custom structured logger (`backend/app/logger.py`) that emits JSON-formatted log lines with timestamp, level, module, and message.

**Log format:**
```
2026-03-13T17:31:48 | INFO | app.main | Starting Ontology Graph Studio v0.1.0 [development]
2026-03-13T17:31:48 | DEBUG | app.ontology.manager | Seeded 5 default ontology classes
2026-03-13T17:35:12 | INFO | app.agents.pipeline | Pipeline completed: run_id=abc123 steps=5/5
```

**Log levels:**
- `DEBUG` — Detailed internal state (dev only)
- `INFO` — Key operational events (service start, pipeline completion, health checks)
- `WARNING` — Recoverable issues (Neo4j offline, vector search failed, low confidence)
- `ERROR` — Failures requiring attention (synthesis error, DB write failed)

### Agent Run Tracking

Every pipeline execution creates an `AgentRun` row in PostgreSQL. Query run history:

```bash
# List recent runs
curl "http://localhost:8000/api/agents/runs?limit=10"

# Get run detail with step timing
curl "http://localhost:8000/api/agents/runs/{run_id}"
```

### Health Endpoints

```bash
# Backend liveness
curl http://localhost:8000/api/health

# Neo4j health (via graph stats)
curl http://localhost:8000/api/graph/stats

# PostgreSQL health (implicit in any DB-backed endpoint)
curl http://localhost:8000/api/ingest
```

### Knowledge Graph Health Metrics

The `/api/learning/metrics` endpoint provides continuous quality monitoring:

```bash
curl http://localhost:8000/api/learning/metrics
```

Key metrics to monitor in production:
- `ontology_coverage` — should be > 0.8 after corpus stabilises
- `duplicate_entities` — should trend toward 0 after auto-correct runs
- `orphan_entities` — high orphan count indicates sparse relationship extraction

### Neo4j Monitoring

Access the built-in Neo4j monitoring at http://localhost:7474:
- **Overview** — Connection count, memory usage, query throughput
- **Query Log** — Slow query detection
- **Schema** — Index and constraint status

For production, enable Neo4j Enterprise metrics export to Prometheus/Grafana.

### Recommended Alerts

| Condition | Action |
|-----------|--------|
| `GET /api/health` returns non-200 | Page on-call — backend down |
| `neo4j_edge_count = 0` and documents exist | Graph build has not been run |
| `ontology_coverage < 0.5` | Knowledge evolution engine needs attention |
| `duplicate_entities > 50` | Run `POST /api/learning/analyze` with `auto_correct: true` |
| Pipeline run stuck in `running` > 15 min | Check agent logs for timeout in AI call |
