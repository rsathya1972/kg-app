# ADR-004: pgvector Instead of a Dedicated Vector Database

**Date**: 2026-01-20
**Status**: Accepted
**Supersedes**: —

---

## Context

The semantic search feature requires vector similarity search over document chunk embeddings (1536 dimensions, text-embedding-3-small). Options considered:
1. PostgreSQL + pgvector extension
2. Pinecone (managed vector DB)
3. Weaviate (open-source vector DB)
4. Qdrant (open-source vector DB)

## Decision

Use **pgvector** (PostgreSQL extension) for vector storage and similarity search.

## Rationale

- **Operational simplicity**: PostgreSQL is already in the stack for relational data. Adding pgvector is a one-line Docker image change (`pgvector/pgvector:pg16`) — no new service to run, monitor, or back up.
- **Correctness**: pgvector supports exact cosine similarity search. At the scale of this application (thousands, not billions, of chunks), index approximation (HNSW/IVFFlat) is unnecessary — exact search is fast enough.
- **Transactional consistency**: Embeddings are stored in the same transaction as the chunk metadata. No risk of vectors existing without their associated document records.
- **Query expressiveness**: Can combine vector search with SQL filters (e.g. `WHERE document_id = ?`) in a single query — complex joins that dedicated vector DBs don't support natively.
- **Cost**: Zero additional infrastructure cost vs. Pinecone's per-vector pricing.

## Trade-offs Accepted

- pgvector performance degrades at very high vector counts (tens of millions+) without approximate indexes. This is not a concern at MVP scale.
- Pinecone/Weaviate have richer metadata filtering and multi-tenancy features. Not needed for single-user MVP.
- If scale becomes an issue, migration to a dedicated vector DB is straightforward — the `embedding_service.py` interface abstracts the storage layer.

## Consequences

- `chunk_embeddings.embedding` column is `Vector(1536)` (pgvector type)
- pgvector extension created at startup in `main.py` lifespan handler
- Must use `pgvector/pgvector:pg16` Docker image (not stock `postgres:16`)
- Tests that touch the embedding column must mock the service (SQLite doesn't have pgvector)
