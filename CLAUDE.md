# Ontology Graph Studio — Claude Context

## What This Project Does

An AI-powered web application that ingests unstructured documents (PDF, DOCX, TXT) and builds an ontology-based knowledge graph. Users define domain ontologies, extract entities and relationships via AI, and explore the resulting graph.

---

## Current State (Step 1 — Foundation)

- FastAPI backend with `GET /api/health` endpoint
- Next.js 15 frontend with header, left nav, home page, and 6 placeholder module pages
- PostgreSQL included in Docker Compose (not yet connected to app logic)
- AI clients (Anthropic, OpenAI) exist as stubs — no real calls yet
- No document ingestion, no entity extraction, no Neo4j

---

## Tech Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Backend    | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2   |
| Frontend   | Next.js 15 (App Router), React 19, TypeScript     |
| Styling    | Tailwind CSS 3                                    |
| DB         | PostgreSQL 16 (asyncpg)                           |
| Graph DB   | Neo4j (planned — Step 5)                         |
| AI         | Anthropic `claude-haiku-4-5-20251001` / `claude-sonnet-4-6` + OpenAI GPT |
| Container  | Docker + Docker Compose                           |

---

## Project Structure

```
kg-app/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI entrypoint
│   │   ├── config.py             Pydantic Settings (env vars)
│   │   ├── logger.py             Structured logging
│   │   ├── api/routes/health.py  GET /api/health
│   │   ├── schemas/health.py     HealthResponse model
│   │   └── ai/
│   │       ├── anthropic_client.py  Claude stub
│   │       └── openai_client.py     OpenAI stub
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/layout.tsx        Root layout (header + nav)
│   │   ├── app/page.tsx          Home (health check + module grid)
│   │   ├── app/upload/page.tsx   Placeholder
│   │   ├── app/extract/page.tsx  Placeholder
│   │   ├── app/ontology/page.tsx Placeholder
│   │   ├── app/graph/page.tsx    Placeholder
│   │   ├── app/query/page.tsx    Placeholder
│   │   ├── app/validation/page.tsx Placeholder
│   │   ├── components/Header.tsx
│   │   ├── components/LeftNav.tsx
│   │   ├── components/StatusBadge.tsx
│   │   ├── lib/api.ts            Typed fetch wrapper
│   │   └── lib/types.ts          Shared TS interfaces
│   └── Dockerfile
├── sample_data/raw/placeholder.txt
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── DECISIONS.md
└── CLAUDE.md
```

---

## Development Guidelines

### Backend
- All routes go in `backend/app/api/routes/` — one file per resource
- All AI logic goes in `backend/app/ai/` — one file per provider/task
- Use `async def` for all route handlers
- Use `run_in_executor` for blocking I/O inside async handlers
- Return structured JSON via Pydantic response models
- All env vars loaded via `app/config.py` Settings — never `os.environ` directly

### Frontend
- All pages under `src/app/` using Next.js App Router
- API calls go through `src/lib/api.ts` — never raw `fetch` in components
- Types in `src/lib/types.ts` — keep in sync with backend response shapes
- Use `"use client"` only on pages/components that need interactivity (event handlers, hooks)
- Tailwind utility classes only — no custom CSS files other than `globals.css`

### AI / Prompt Engineering
- Use `claude-haiku-4-5-20251001` for extraction/parsing tasks (fast, cheap)
- Use `claude-sonnet-4-6` for generation/reasoning tasks (quality)
- Always instruct Claude to return "ONLY valid JSON, no markdown fences"
- Strip markdown fences from responses before JSON.parse
- Include "NEVER fabricate" instruction in every extraction prompt

---

## Planned Incremental Steps

| Step | Description |
|------|-------------|
| 2 | PostgreSQL models, document upload, file storage |
| 3 | AI entity extraction pipeline (NER, relationships) |
| 4 | Ontology CRUD (classes, properties, constraints) |
| 5 | Neo4j integration, graph write |
| 6 | Graph viewer (D3 / Cytoscape) |
| 7 | Natural language query → Cypher |
| 8 | SHACL validation engine |
| 9 | Export (RDF/OWL, JSON-LD) |

---

## Running the App

```bash
# Local (no Docker)
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

# Docker
docker compose up --build
```

Backend health: http://localhost:8000/api/health
Frontend: http://localhost:3000
API docs: http://localhost:8000/docs
