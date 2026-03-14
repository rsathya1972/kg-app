# ADR-002: Dual Database — PostgreSQL + Neo4j

**Date**: 2026-01-15
**Status**: Accepted
**Supersedes**: —

---

## Context

The application needs to store:
1. Raw documents, extracted entities, embeddings, agent run history (relational/tabular data)
2. An entity-relationship graph with traversal queries (graph data)

Using a single database means compromising on one of these.

## Decision

Use **PostgreSQL 16** (with pgvector) for all relational data and **Neo4j 5** for the knowledge graph. Both run as Docker Compose services.

## Rationale

**PostgreSQL is used for:**
- Documents, entities, relationships (source of truth for AI extraction results)
- Vector embeddings via `pgvector` extension (cosine similarity search)
- Ontology versions, agent run history, knowledge issues, proposals
- ACID transactions for pipeline state

**Neo4j is used for:**
- Graph traversal queries (k-hop neighborhoods, path finding)
- Pattern matching across entity types
- Cypher query execution (NL → Cypher workflow)
- Graph visualization data source

**Why not a single graph database?**
- Neo4j lacks first-class vector search (pgvector is production-grade)
- PostgreSQL is easier to operate, backup, and restore than Neo4j
- Relational queries (e.g. "all documents with confidence < 0.5") are awkward in Cypher

**Why not a single relational database?**
- Multi-hop graph traversal in SQL (recursive CTEs) is verbose and slow compared to Cypher
- Graph visualization tools integrate natively with Neo4j

## Consequences

- Data exists in two places: `extracted_entities` in PostgreSQL and nodes in Neo4j
- `GraphBuilderService` is responsible for syncing PostgreSQL extraction results → Neo4j (via `pg_id` as the cross-store key)
- Graph build is idempotent (uses Cypher MERGE) — safe to re-run
- Neo4j startup is optional for development — backend degrades gracefully if Neo4j is down
- Two connection pools to manage and monitor
