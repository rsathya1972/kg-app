# Architecture Decision Records — Ontology Graph Studio

## ADR-001: FastAPI over Django/Flask

**Decision**: Use FastAPI as the backend framework.

**Rationale**:
- Native async/await support — critical for concurrent AI API calls
- OpenAPI docs generated automatically (zero overhead)
- Pydantic integration for schema validation
- Smaller footprint than Django for an API-only service

---

## ADR-002: Next.js 15 App Router

**Decision**: Use Next.js 15 with the App Router (not Pages Router).

**Rationale**:
- Server Components reduce client-side JS bundle
- File-system routing maps cleanly to module structure
- Built-in TypeScript support, layout nesting, and loading states
- Active development trajectory (Vercel-backed)

---

## ADR-003: PostgreSQL for Metadata, Neo4j for Graph

**Decision**: Use PostgreSQL for relational metadata and Neo4j for the knowledge graph.

**Rationale**:
- PostgreSQL is battle-tested for document metadata, job state, and ontology definitions (structured, relational data)
- Neo4j provides native graph traversal and Cypher — the right tool for graph queries that would be painful in SQL
- Separation of concerns: metadata store vs. graph store

**Trade-off**: Two databases increase operational complexity. Acceptable for enterprise ontology tooling where graph query performance matters.

---

## ADR-004: AI Client Stubs at Foundation Step

**Decision**: Include Anthropic and OpenAI client files as stubs (raising `NotImplementedError`) rather than fully wired clients.

**Rationale**:
- Establishes the module boundary and import pattern early
- Allows route handlers to import `anthropic_client` without breaking
- Avoids burning API credits before pipelines are designed

---

## ADR-005: No Vector Database

**Decision**: No vector database (Pinecone, Weaviate, Chroma) in the initial design.

**Rationale**:
- Claude's 200k token context window fits all entity candidates + ontology for alignment in one call
- Neo4j supports vector indexes natively (from v5.11) if semantic search is needed later
- Avoid complexity until retrieval performance becomes a measured bottleneck

---

## ADR-006: Tailwind CSS (not CSS Modules or styled-components)

**Decision**: Use Tailwind CSS utility classes exclusively.

**Rationale**:
- Zero context switching between markup and styles
- Consistent design tokens via config
- Tree-shaking eliminates unused classes in production
- Dark theme built on slate color palette without additional libraries

---

## ADR-007: SQLAlchemy (async) over raw asyncpg

**Decision**: Use SQLAlchemy 2.0 async engine over raw asyncpg.

**Rationale**:
- ORM layer will be needed for models (documents, jobs, ontologies)
- SQLAlchemy 2.0 async is production-ready and well-documented
- Alembic migrations integrate cleanly
- Can drop to raw SQL via `text()` when needed

---

## ADR-008: Docker Compose for Local Dev

**Decision**: Docker Compose orchestrates Postgres + backend + frontend locally.

**Rationale**:
- Eliminates "works on my machine" issues for PostgreSQL setup
- Frontend developer can `docker compose up` without Python knowledge
- Production deployment strategy (cloud) deferred — Compose is the right scope for MVP

---

## ADR-009: Module-Per-Domain Package Layout

**Decision**: Organize backend code into one Python package per domain module (`ingestion`, `preprocessing`, `extraction`, `ontology`, `graph`, `query`, `validation`, `utils`).

**Rationale**:
- Each domain has a clear `base.py` defining its ABC/dataclasses — a stable contract
- New developers can find all ingestion logic in one place, all graph logic in another
- Stubs follow the same pattern as real implementations — swap in without touching route code
- `utils/` is a shared toolkit imported by all modules with no circular dependencies

**Trade-off**: More files than a flat layout, but necessary for a platform that will grow to 50+ files.

---

## ADR-010: Stubs Raise NotImplementedError, Routes Return HTTP 501

**Decision**: Unimplemented service methods raise `NotImplementedError`; API routes catch this and return HTTP 501 `{"status": "not_implemented"}`.

**Rationale**:
- Routes are immediately testable (Swagger, curl) without any real logic
- `NotImplementedError` gives a clear traceback pointing to exactly which stub needs work
- Consistent pattern across all 7 domain modules
- Avoids silent no-ops that could be mistaken for working implementations
