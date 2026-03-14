# Query Module

Translates natural language questions into Cypher queries and/or semantic search answers.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | `StructuredQuery` dataclass |
| `nl_parser.py` | Stub — NL → `StructuredQuery` via Claude Sonnet |
| `cypher_builder.py` | Stub — `StructuredQuery` → Cypher string |
| `executor.py` | Stub — Cypher execution wrapper |

---

## Current Architecture

The query pipeline has two parallel paths, both triggered by `POST /api/query`:

### Path 1 — Direct Cypher (live)
`backend/app/agents/query_agent.py` → `QueryPlanningAgent`

1. User question → Claude Haiku (PROMPT-003) → raw Cypher string
2. Strip markdown fences
3. Execute via `neo4j_client.run(cypher)`
4. Return results as list of dicts

### Path 2 — GraphRAG / Semantic (live)
`backend/app/agents/rag_agent.py` → `GraphRAGAgent`

1. User question → OpenAI embedding → pgvector cosine search → top-K chunks
2. Chunks + question → Claude Sonnet (PROMPT-004) → natural language answer
3. Return answer + source citations

Both paths run in parallel on each request. Results merged in the route handler.

---

## Planned Architecture (Step 7)

The stubs in this module implement a more structured two-step pipeline:

```
NL question
    ↓
nl_parser.py → StructuredQuery (intent, entity_types, filters, relations, limit)
    ↓
cypher_builder.py → Type-safe Cypher string (no string interpolation)
    ↓
executor.py → Neo4j results
```

This replaces the ad-hoc Cypher generation in `query_agent.py` with a structured intermediate representation, enabling:
- Input validation before Cypher execution
- Better error messages when a query can't be executed
- Cypher injection prevention (parameterized queries from structured types)

---

## StructuredQuery

```python
@dataclass
class StructuredQuery:
    intent: str          # "find" | "count" | "relate" | "path"
    entity_types: list[str]  # e.g. ["Company", "Technology"]
    filters: dict        # e.g. {"confidence": {"gte": 0.7}}
    relations: list[str] # e.g. ["USES", "OWNS"]
    limit: int           # default 25
```

---

## How to Add a New Query Intent

When Step 7 is implemented:

1. Add the intent string to `StructuredQuery.intent` type hint
2. Add a branch in `cypher_builder.py` `build(query: StructuredQuery) → str`
3. Update PROMPT-006 in `nl_parser.py` to include the new intent in the valid values list
4. Update `PROMPTS.md` PROMPT-006 entry
5. Write a test in `tests/test_query_agent.py`
