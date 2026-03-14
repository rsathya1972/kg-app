# Database Module

PostgreSQL connection management and ORM model definitions.

---

## Files

| File | Purpose |
|------|---------|
| `database.py` | Async engine, `AsyncSession` dependency, `create_tables()` |
| `models.py` | All 8 SQLAlchemy ORM models |

---

## Engine Setup

```python
# In database.py
engine = create_async_engine(settings.DATABASE_URL, echo=False)

async def get_session() -> AsyncSession:
    async with AsyncSession(engine) as session:
        yield session
```

Inject `db: AsyncSession = Depends(get_session)` into route handlers.

## Table Auto-Creation

Tables are created at startup in `main.py` lifespan handler:

```python
async with engine.begin() as conn:
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await conn.run_sync(Base.metadata.create_all)
```

> `create_all` is idempotent — safe to run on every startup. For schema migrations (adding columns, changing types), use Alembic.

---

## Models Overview

See `SCHEMA.md` for full column definitions.

| Model | Table | Purpose |
|-------|-------|---------|
| `Document` | `documents` | Ingested raw documents |
| `ChunkEmbedding` | `chunk_embeddings` | OpenAI vector embeddings |
| `ExtractedEntity` | `extracted_entities` | AI-extracted named entities |
| `ExtractedRelationship` | `extracted_relationships` | AI-extracted relationships |
| `OntologyVersion` | `ontology_versions` | Versioned ontology snapshots |
| `AgentRun` | `agent_runs` | Pipeline execution history |
| `KnowledgeIssue` | `knowledge_issues` | Detected graph quality issues |
| `OntologyProposal` | `ontology_proposals` | AI-generated ontology changes |

---

## Relationships

```
Document ──< ChunkEmbedding       (one document, many chunks)
Document ──< ExtractedEntity      (one document, many entities)
Document ──< ExtractedRelationship
ExtractedEntity ──< ExtractedRelationship  (source + target)
Document ──< AgentRun
```

All foreign keys cascade on delete (`ondelete="CASCADE"`).

---

## Adding a New Table

1. Define a new SQLAlchemy model class in `models.py` inheriting from `Base`
2. Add to `SCHEMA.md` with full column definitions
3. Run the app — `create_all` will auto-create the table on next startup
4. For production: generate an Alembic migration instead of relying on `create_all`

---

## Migrations (Future)

Currently using `create_all` (development only). Before production:

```bash
cd backend
alembic init migrations
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
