# Architecture — Ontology Graph Studio

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                         │
│  Next.js 15 (React 19 + TypeScript + Tailwind)                  │
│  localhost:3000                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/JSON
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python 3.11)                                   │
│  localhost:8000                                                  │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  API Routes │  │  AI Clients  │  │  Core Services         │  │
│  │  /api/health│  │  Anthropic   │  │  Document Ingestion    │  │
│  │  /api/docs  │  │  OpenAI      │  │  Entity Extraction     │  │
│  │  (planned)  │  │  (stubs)     │  │  Graph Writer          │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└──────┬──────────────────────────────────────────┬───────────────┘
       │ SQLAlchemy (asyncpg)                      │ Neo4j driver (planned)
       ▼                                           ▼
┌─────────────────────┐                ┌──────────────────────────┐
│  PostgreSQL 16       │                │  Neo4j (planned)         │
│  Metadata store      │                │  Graph store             │
│  • Documents         │                │  • Nodes (entities)      │
│  • Ontologies        │                │  • Edges (relationships) │
│  • Job state         │                │  • Labels & properties   │
└─────────────────────┘                └──────────────────────────┘
```

---

## Component Responsibilities

### Frontend (`frontend/`)

| File/Dir | Responsibility |
|----------|---------------|
| `src/app/layout.tsx` | Root shell: fixed header + left nav |
| `src/app/page.tsx` | Dashboard: backend status + module links |
| `src/app/*/page.tsx` | Module placeholder pages |
| `src/components/Header.tsx` | Top navigation bar |
| `src/components/LeftNav.tsx` | Sidebar with route-aware active state |
| `src/components/StatusBadge.tsx` | Live backend health indicator |
| `src/lib/api.ts` | Typed fetch wrapper for all backend calls |
| `src/lib/types.ts` | Shared TypeScript interfaces |

### Backend (`backend/`)

| File/Dir | Responsibility |
|----------|---------------|
| `app/main.py` | FastAPI app, CORS, lifespan, router mounting |
| `app/config.py` | Pydantic Settings: env var loading |
| `app/logger.py` | Structured logging (stdout, timestamped) |
| `app/api/routes/health.py` | `GET /api/health` — liveness check |
| `app/schemas/health.py` | `HealthResponse` Pydantic model |
| `app/ai/anthropic_client.py` | Anthropic Claude wrapper (stub) |
| `app/ai/openai_client.py` | OpenAI wrapper (stub) |

---

## Data Flow — Document to Graph (Planned)

```
User uploads document
        │
        ▼
POST /api/documents/upload
        │
        ▼
Document stored in PostgreSQL (metadata) + filesystem
        │
        ▼
AI Pipeline: Entity Extraction
  ├── NER (Named Entity Recognition)
  ├── Relationship Detection
  └── Event Extraction
        │
        ▼
Ontology Alignment
  ├── Map extracted types → ontology classes
  ├── Validate against constraints (SHACL)
  └── Resolve conflicts
        │
        ▼
Graph Write (Neo4j)
  ├── CREATE nodes with labels and properties
  └── CREATE relationships with types
        │
        ▼
User queries graph via Graph Viewer / Query module
```

---

## AI Pipeline Strategy

| Task | Model | Rationale |
|------|-------|-----------|
| Text chunking & metadata | Haiku | Fast, cheap, deterministic |
| Entity extraction (NER) | Haiku | High throughput, JSON output |
| Relationship detection | Sonnet | Requires stronger reasoning |
| Ontology alignment | Sonnet | Complex multi-step reasoning |
| Query translation (NL→Cypher) | Sonnet | Precision matters |
| Summary / explanations | Haiku | Low stakes, fast |

---

## Storage Strategy

| Data Type | Store | Rationale |
|-----------|-------|-----------|
| Document metadata, job state, ontology definitions | PostgreSQL | ACID, relational queries |
| Graph nodes and edges | Neo4j | Native graph traversal, Cypher |
| Raw document files | Local filesystem (Docker volume) | Simple for MVP |

---

## Planned Incremental Steps

1. **Step 1 (current)**: Scaffold, health endpoint, UI shell
2. **Step 2**: PostgreSQL models, document upload, file storage
3. **Step 3**: AI entity extraction pipeline
4. **Step 4**: Ontology CRUD (classes, properties, constraints)
5. **Step 5**: Neo4j integration, graph write
6. **Step 6**: Graph viewer (D3 / Cytoscape)
7. **Step 7**: Natural language query → Cypher
8. **Step 8**: SHACL validation engine
9. **Step 9**: Export (RDF/OWL, JSON-LD)
