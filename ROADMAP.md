# Ontology Graph Studio — Roadmap

> Last updated: 2026-03-13

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Done — live and working |
| 🔨 | In progress — partially implemented |
| 📋 | Planned — not started |
| 🚫 | Blocked — depends on another step |

---

## Foundation (Step 1) ✅

- [x] FastAPI backend skeleton + health endpoint
- [x] Next.js 15 frontend with App Router, header, left nav
- [x] Docker Compose: PostgreSQL 16 (pgvector), Neo4j 5, backend, frontend
- [x] AI client stubs (Anthropic, OpenAI)
- [x] CORS, structured logging, pydantic settings
- [x] Project documentation: CLAUDE.md, ARCHITECTURE.md, DECISIONS.md

---

## Step 2 — Storage + Document Ingestion ✅

- [x] PostgreSQL models (8 tables): Document, ChunkEmbedding, ExtractedEntity, ExtractedRelationship, OntologyVersion, AgentRun, KnowledgeIssue, OntologyProposal
- [x] pgvector extension auto-provisioned on startup
- [x] File ingester: TXT, PDF (pypdf), DOCX (python-docx)
- [x] MIME type detection (python-magic)
- [x] Ingestion API routes: `POST /api/ingest`, `POST /api/ingest/upload`, `GET /api/ingest`, `GET /api/ingest/{id}`, `DELETE /api/ingest/{id}`
- [x] Text preprocessing: SlidingWindowChunker, SentenceChunker, text cleaner utilities

---

## Step 3 — AI Extraction Pipeline ✅

- [x] Entity extraction (Claude Haiku): 8 entity types, sliding-window chunking, deduplication
- [x] Relationship extraction (Claude Haiku): 10 relationship types, entity-aware chunking, deduplication
- [x] Extraction persisted to PostgreSQL (`extracted_entities`, `extracted_relationships`)
- [x] OpenAI embeddings (text-embedding-3-small, 1536 dims) stored via pgvector
- [x] Semantic search: `embedding_service.semantic_search(query, top_k, db)`
- [x] Vector memory routes: embed document, search

---

## Step 4 — Ontology Management 🔨

- [x] In-memory ontology manager (5 default classes: Entity, Person, Organization, Location, Concept)
- [x] Ontology CRUD API routes (in-memory, not persisted)
- [ ] **Persist ontology to PostgreSQL** via `OntologyVersion` model
- [ ] **Ontology alignment agent** (`backend/app/ontology/aligner.py` — currently `NotImplementedError`)
  - Map extracted entities → ontology classes via Claude Sonnet
  - Store alignment confidence in `ExtractedEntity.attributes_json`
- [ ] Ontology versioning: snapshot before/after changes
- [ ] Frontend: Ontology Builder page (currently placeholder)

---

## Step 5 — Neo4j Graph Integration ✅ (core) / 🔨 (advanced)

- [x] Neo4j async client (bolt connection, Cypher execution)
- [x] Graph builder: MERGE entities + relationships into Neo4j (idempotent)
- [x] Graph reader: neighborhood traversal, document graph, stats
- [x] Graph build API: `POST /api/graph/build/{document_id}`
- [ ] **APOC plugin integration** (currently used in `reader.py` but requires APOC jar)
- [ ] **Relationship type migration**: current model uses generic `RELATES` edge with `type` property; migrate to typed relationships (`:WORKS_FOR`, `:OWNS`, etc.) for query performance
- [ ] **Graph schema constraints**: add Neo4j uniqueness constraint on `pg_id`

---

## Step 6 — Graph Viewer 🔨

- [x] ReactFlow (XYFlow) installed in frontend
- [ ] **Graph visualization page** (`/graph` — currently placeholder)
  - Fetch node/edge data from `GET /api/graph/document/{id}`
  - Render interactive graph with XYFlow
  - Node coloring by entity type
  - Edge labels showing relationship type
  - Click-to-expand neighborhood
- [ ] Force-directed layout
- [ ] Filter by entity type / relationship type
- [ ] Export graph as PNG/SVG

---

## Step 7 — Natural Language Query ✅ (RAG) / 🔨 (Cypher)

- [x] RAG agent: semantic search → Claude Sonnet grounded answer
- [x] Query agent: NL → Cypher via Claude Haiku → Neo4j execution
- [x] `POST /api/query` combining both
- [ ] **NL parser** (`backend/app/query/nl_parser.py` — currently `NotImplementedError`)
  - Parse NL → `StructuredQuery` (intent, entity_types, filters, relations, limit)
  - Feed structured query to `CypherBuilder` for type-safe Cypher generation
- [ ] **CypherBuilder** (`backend/app/query/cypher_builder.py` — stub)
- [ ] Frontend: Query page with results table + graph visualization toggle

---

## Step 8 — Validation Engine 📋

- [ ] **SHACL validator** (`backend/app/validation/shacl_validator.py` — stub)
  - Validate nodes/edges against user-defined constraints
  - Severity levels: ERROR, WARNING, INFO
- [ ] **Consistency checker** (`backend/app/validation/consistency_checker.py` — stub)
  - Detect orphan nodes, duplicate entities, contradicting relationships
- [ ] `POST /api/validation/run` endpoint
- [ ] Validation report UI

---

## Step 9 — Knowledge Health + Evolution ✅

- [x] KnowledgeEvolutionEngine: detect 6 issue types (low confidence, orphan nodes, missing properties, duplicate names, sparse subgraph, conflicting types)
- [x] Proposal generation via Claude Haiku (add_class, merge_class, rename_class, add_relationship)
- [x] `POST /api/learning/analyze` + apply proposals
- [x] Knowledge Health dashboard page
- [ ] Auto-correction scheduling (cron or triggered)
- [ ] Proposal review UI (approve / reject / defer)

---

## Step 10 — Export + Observability 📋

- [ ] RDF/OWL export (N-Triples, Turtle)
- [ ] JSON-LD export
- [ ] Structured logging improvements (trace IDs per pipeline run)
- [ ] Agent run dashboard (fully wired, currently partial)
- [ ] Prometheus metrics endpoint
- [ ] API rate limiting

---

## Backlog / Nice-to-Have

- [ ] Web URL ingestion (currently stub in `ingestion/registry.py`)
- [ ] PDF table extraction (beyond pypdf text layer)
- [ ] Multi-language support (language detection stub exists)
- [ ] Event extraction (`extraction/event_extractor.py` — stub)
- [ ] Semantic versioning for ontology changes
- [ ] User authentication (currently single-user, no auth)
- [ ] Bulk document ingestion (zip upload)
- [ ] Document re-processing (update embeddings + graph on edit)
