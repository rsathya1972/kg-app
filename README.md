# Ontology Graph Studio

AI-powered application that transforms unstructured documents into structured, queryable ontology-based knowledge graphs.

---

## Quick Start (Local, No Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # edit .env and fill in API keys
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # set NEXT_PUBLIC_API_URL if needed
npm run dev
```

Open: http://localhost:3000

---

## Quick Start (Docker Compose)

```bash
cp .env.example .env              # fill in ANTHROPIC_API_KEY, OPENAI_API_KEY
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API Docs | http://localhost:8000/docs   |
| Postgres | localhost:5432               |

---

## Project Structure

```
kg-app/
├── backend/          FastAPI application (Python 3.11)
├── frontend/         Next.js 15 application (TypeScript)
├── sample_data/      Sample documents for testing
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── DECISIONS.md
└── CLAUDE.md
```

---

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python 3.11, FastAPI, Pydantic    |
| Frontend  | Next.js 15, React 19, TypeScript  |
| Styling   | Tailwind CSS 3                    |
| Database  | PostgreSQL 16 (metadata)          |
| Graph DB  | Neo4j (planned — later step)      |
| AI        | Anthropic Claude + OpenAI         |
| Container | Docker + Docker Compose           |

---

## Environment Variables

Copy `.env.example` to `.env` and set:

| Variable            | Required | Description                        |
|---------------------|----------|------------------------------------|
| `ANTHROPIC_API_KEY` | Yes      | Anthropic Claude API key           |
| `OPENAI_API_KEY`    | Yes      | OpenAI API key                     |
| `POSTGRES_DB`       | No       | PostgreSQL database name           |
| `POSTGRES_USER`     | No       | PostgreSQL username                |
| `POSTGRES_PASSWORD` | No       | PostgreSQL password                |
| `ENV`               | No       | `development` or `production`      |

---

## Development Status

- [x] Project scaffold and monorepo structure
- [x] FastAPI backend with health endpoint
- [x] Next.js frontend shell with nav and home page
- [x] Docker Compose multi-service setup
- [ ] Document ingestion pipeline
- [ ] AI entity extraction
- [ ] Ontology editor
- [ ] Neo4j graph integration
- [ ] Graph visualizer
- [ ] Natural language query interface
- [ ] SHACL validation engine
# kg-app
