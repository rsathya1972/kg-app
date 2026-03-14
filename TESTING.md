# Ontology Graph Studio — Testing Guide

---

## Test Stack

| Tool | Purpose |
|------|---------|
| `pytest` | Backend test runner |
| `pytest-asyncio` | Async test support |
| `unittest.mock` | Mock Claude/OpenAI API calls |
| `httpx.AsyncClient` | FastAPI route testing (via `TestClient`) |

---

## Running Tests

```bash
# All backend tests
cd backend
source venv/bin/activate
pytest

# With verbose output
pytest -v

# A specific file
pytest tests/test_entity_extractor.py -v

# A specific test
pytest tests/test_entity_extractor.py::test_extracts_company_entity -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

---

## Test Layout

```
backend/tests/
├── conftest.py                  # Shared fixtures (DB session, mock AI clients)
├── test_ingestion.py            # FileIngester, text ingestion, MIME detection
├── test_entity_extractor.py     # EntityExtractionAgent (mocked Claude)
├── test_relation_extractor.py   # RelationExtractor (mocked Claude)
├── test_embedding_service.py    # VectorEmbeddingService (mocked OpenAI)
├── test_graph_builder.py        # GraphBuilderService (mocked Neo4j)
├── test_query_agent.py          # QueryPlanningAgent + GraphRAGAgent (mocked)
├── test_knowledge_evolution.py  # KnowledgeEvolutionEngine (mocked Claude)
├── test_ontology_manager.py     # OntologyManager CRUD
└── test_routes/
    ├── test_ingest_routes.py    # POST/GET /api/ingest/*
    ├── test_graph_routes.py     # POST/GET /api/graph/*
    └── test_query_routes.py     # POST /api/query
```

---

## Mocking Strategy

### Rule: Never call real AI APIs in tests

Claude and OpenAI calls are expensive and non-deterministic. Always mock them.

```python
# Mocking Claude Haiku in a test
from unittest.mock import AsyncMock, patch

@patch("app.ai.anthropic_client.anthropic_client.complete")
async def test_entity_extraction(mock_complete):
    mock_complete.return_value = json.dumps({
        "entities": [
            {"name": "Acme Corp", "type": "Company", "attributes": {}, "evidence": "Acme Corp is...", "confidence": 0.95}
        ]
    })
    result = await entity_extractor.extract(sample_text)
    assert len(result.entities) == 1
    assert result.entities[0].name == "Acme Corp"
```

### Rule: Never call real Neo4j in tests

Use mocked `neo4j_client.run()`:

```python
@patch("app.graph.neo4j_client.neo4j_client.run")
async def test_graph_builder(mock_run):
    mock_run.return_value = [{"was_created": True}]
    result = await graph_builder.build(entities=sample_entities, relationships=[])
    assert result["nodes_created"] == len(sample_entities)
```

### Rule: Use an in-memory SQLite DB for route tests

Never depend on the real PostgreSQL instance in CI:

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.db.database import Base

@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
```

> Note: pgvector types are not available in SQLite. Tests that exercise the `embedding` column must mock `embedding_service` entirely.

---

## What to Test Per Module

### Ingestion (`test_ingestion.py`)
- `FileIngester.ingest()` with TXT, PDF, DOCX files (use real fixture files in `tests/fixtures/`)
- MIME type detection from extension fallback
- Empty file handling
- Oversized file rejection (if size limits are added)

### Entity Extraction (`test_entity_extractor.py`)
- Happy path: JSON with entities → parsed `Entity` objects
- Deduplication: two chunks yield same entity → highest confidence kept
- JSON parse failure: malformed Claude response → logged, skipped, no crash
- Unknown entity type in response → still ingested (do not reject unknown types)
- Zero-entity response: `{"entities": []}` → empty result, no error
- Prompt structure: assert mock called with correct system prompt snippet

### Relationship Extraction (`test_relation_extractor.py`)
- Only called for chunks with ≥2 entity names (smart-chunking optimization)
- (source, type, target) triple deduplication
- Source/target not in entity list → relationship discarded
- Unknown relationship type → still ingested

### Vector Embeddings (`test_embedding_service.py`)
- `embed_document()`: assert OpenAI called once per chunk, results stored
- Idempotency: second call deletes previous rows before inserting new ones
- `semantic_search()`: assert correct pgvector query issued, results ranked by similarity

### Graph Builder (`test_graph_builder.py`)
- MERGE idempotency: running twice does not duplicate nodes
- Entity type → Neo4j label conversion (`_safe_label()`)
- `was_created` flag tracking (nodes_created vs nodes_updated counts)

### Query Agent (`test_query_agent.py`)
- Markdown fence stripping before Cypher execution
- Cypher execution error → returned in `error` field, no exception
- RAG agent: top-K results used in context, answer references sources

### Knowledge Evolution (`test_knowledge_evolution.py`)
- Each of 6 issue types detected correctly with fixture data
- Proposal generation: Claude response → `OntologyProposal` objects
- `auto_correct=True` path applies approved proposals
- `confidence_threshold` correctly filters entities

### Ontology Manager (`test_ontology_manager.py`)
- Default 5 classes seeded on init
- `create_class()` / `delete_class()` lifecycle
- `get_class_by_name()` case-insensitive match
- Deleting non-existent class → raises `KeyError` or returns `False`

---

## Test Fixtures

Place sample documents in `backend/tests/fixtures/`:

```
tests/fixtures/
├── sample.txt          # Short plain-text document for ingestion tests
├── sample.pdf          # Simple PDF (test PDF extraction)
├── sample.docx         # Simple DOCX (test DOCX extraction)
└── claude_responses/
    ├── entities.json   # Sample valid entity extraction response
    ├── relations.json  # Sample valid relation extraction response
    └── cypher.txt      # Sample Cypher query from query agent
```

---

## Coverage Targets

| Module | Target |
|--------|--------|
| `extraction/` | ≥ 90% |
| `ingestion/` | ≥ 85% |
| `vector_memory/` | ≥ 80% |
| `graph/` | ≥ 75% |
| `agents/` | ≥ 75% |
| `api/routes/` | ≥ 70% |
| `ontology/` | ≥ 70% |
| Stubs (`NotImplementedError`) | Excluded |

---

## CI Notes

- Tests run on every PR via GitHub Actions (when configured)
- Never use `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in CI — all AI calls must be mocked
- Use `pytest-asyncio` mode `auto` (set in `pyproject.toml` or `pytest.ini`)
- pgvector types unavailable in CI SQLite — mock embedding service entirely for route tests
