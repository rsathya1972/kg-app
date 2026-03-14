# Graph Module

Writes extracted entities and relationships into Neo4j and reads graph data for visualization and traversal.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | Base classes |
| `neo4j_client.py` | `Neo4jClient` singleton — async Cypher execution |
| `writer.py` | `GraphBuilderService` — MERGE entities/relationships into Neo4j |
| `reader.py` | `GraphReader` — neighborhood traversal, document graph, stats |

---

## Neo4j Client

Singleton initialized at app startup in `main.py` lifespan handler.

```python
from app.graph.neo4j_client import neo4j_client

# Execute arbitrary Cypher
results = await neo4j_client.run(
    "MATCH (n {pg_id: $id}) RETURN n",
    {"id": entity_id}
)
```

Connection params: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` from `config.py`.
If Neo4j is unreachable at startup, the app logs a warning and continues (Neo4j-dependent routes return HTTP 503).

---

## Graph Builder

Writes extraction results to Neo4j. **Idempotent** — uses `MERGE` so safe to call multiple times.

```python
from app.graph.writer import GraphBuilderService

builder = GraphBuilderService()
result = await builder.build(
    entities=[Entity(...)],
    relationships=[Relation(...)]
)
# result = {"nodes_created": 5, "nodes_updated": 2, "edges_created": 8, "edges_updated": 1}
```

### Node label mapping

Entity type → Neo4j label via `_safe_label()`:
- `"Company"` → `:Company`
- `"Technology"` → `:Technology`
- Unknown type → `:Entity` (fallback)

### Cross-store key

`pg_id` = PostgreSQL UUID from `extracted_entities.id`. Used as the unique identifier in Neo4j to allow cross-store joins without a separate sync service.

---

## Graph Reader

```python
from app.graph.reader import GraphReader

reader = GraphReader()

# All nodes/edges for a document
graph = await reader.get_document_graph(document_id="...")
# graph = {"nodes": [...], "edges": [...]}

# k-hop neighborhood
neighborhood = await reader.get_neighborhood(pg_id="...", depth=2)

# Aggregate stats
stats = await reader.get_stats()
# stats = {"node_count": 42, "edge_count": 87, "label_distribution": {...}}
```

---

## Current Limitations

- All edges use generic `RELATES` type with `r.type` property (see ADR-005)
- APOC plugin required for `get_neighborhood()` — ensure Neo4j APOC jar is included in Docker image
- No uniqueness constraint on `pg_id` yet (planned for Step 5)

---

## How to Write New Cypher Queries

1. Add the method to `reader.py` or `writer.py`
2. Use `await neo4j_client.run(cypher, params)` — always parameterize values (never f-strings)
3. Return plain dicts (the client converts `neo4j.graph.Node` → dict)
4. Add a curl example to `SCHEMA.md` Cypher section if it's a commonly useful query
