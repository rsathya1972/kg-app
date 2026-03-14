# ADR-005: Generic RELATES Edges in Neo4j (Temporary)

**Date**: 2026-02-01
**Status**: Accepted — marked for revision in Step 5
**Supersedes**: —

---

## Context

Neo4j relationship types are fixed at edge creation time and cannot be changed without deleting and recreating the edge. The AI extraction pipeline extracts 10 relationship types (WORKS_FOR, OWNS, USES, etc.). Two design options:

1. **Typed edges**: Each relationship is a distinct Neo4j relationship type (`:WORKS_FOR`, `:OWNS`, `:USES`, etc.)
2. **Generic RELATES edge**: All relationships use a single `RELATES` type, with the specific type stored as a property (`r.type = "WORKS_FOR"`)

## Decision

Use **generic `RELATES` edges** with a `type` property for now. Migrate to typed edges in Step 5.

## Rationale

- **Flexibility during development**: Adding a new relationship type in `RELATIONSHIP_TYPES` doesn't require a graph schema migration
- **Simpler graph builder**: `GraphBuilderService` doesn't need to dynamically construct relationship type strings in Cypher (which requires `apoc.merge.relationship` or string interpolation — both awkward)
- **Safe MERGE**: `MERGE (a)-[r:RELATES]->(b)` is straightforward; `MERGE (a)-[r:{dynamic_type}]->(b)` requires APOC

## Trade-offs Accepted

- Cypher queries must filter on `r.type = 'WORKS_FOR'` rather than pattern-matching on `[:WORKS_FOR]`
- Slightly less query performance (property filter vs. relationship type index)
- Neo4j Browser visualization shows all edges as `RELATES` — less readable

## Migration Plan (Step 5)

When relationship types are stable:
1. `MATCH (a)-[r:RELATES]->(b) WITH a, r, b, r.type AS rel_type DELETE r WITH a, b, rel_type CALL apoc.merge.relationship(a, rel_type, {}, r_props, b) YIELD rel RETURN rel`
2. Update `GraphBuilderService.build()` to use dynamic relationship type creation
3. Update `GraphReader` Cypher queries accordingly
4. Update PROMPT-002 and `RELATIONSHIP_TYPES` to ensure new types are intentional

## Consequences

- All Cypher examples in `SCHEMA.md` and `technical-guide.md` use `RELATES` with property filter
- `graph/reader.py` neighborhood queries filter on `r.type` not relationship type
- APOC plugin not required for current implementation (typed edge migration will require it)
