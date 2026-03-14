# Vector Memory Module

Generates and stores OpenAI text embeddings for document chunks, and provides semantic similarity search via pgvector.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | `EmbedResult`, `SearchResult` dataclasses |
| `embedding_service.py` | `VectorEmbeddingService` — embed + search |

---

## Key Class

### `VectorEmbeddingService`

```python
from app.vector_memory.embedding_service import embedding_service

# Embed all chunks of a document (idempotent — deletes previous embeddings first)
result: EmbedResult = await embedding_service.embed_document(
    document_id="<uuid>",
    db=session
)
# result.chunks_created: int
# result.model_used: "text-embedding-3-small"

# Semantic search
results: list[SearchResult] = await embedding_service.semantic_search(
    query="contract renewal terms",
    top_k=5,
    db=session
)
# results[0].similarity_score: 0.92
# results[0].text: chunk text
# results[0].filename: source document name
```

---

## Embedding Model

| Setting | Value |
|---------|-------|
| Model | `text-embedding-3-small` (OpenAI) |
| Dimensions | 1536 |
| Config key | `OPENAI_EMBEDDING_MODEL`, `VECTOR_DIMENSIONS` |

Input text is truncated to 32k characters before embedding (OpenAI model limit protection).

---

## Storage

Embeddings stored in `chunk_embeddings` table:
- `embedding` column is `Vector(1536)` (pgvector type)
- Cosine distance used for similarity search
- pgvector extension created at startup via `CREATE EXTENSION IF NOT EXISTS vector`

---

## Idempotency

`embed_document()` deletes all existing `ChunkEmbedding` rows for the document before inserting new ones. Re-embedding a document is safe and produces consistent results.

---

## Chunking

Uses `SlidingWindowChunker` from `backend/app/preprocessing/chunker.py`:
- Default: 1000 tokens per chunk, 100 token overlap
- Configurable via `MAX_CHUNK_SIZE`, `CHUNK_OVERLAP` in settings

---

## How to Change Embedding Model

1. Update `OPENAI_EMBEDDING_MODEL` in `.env`
2. Update `VECTOR_DIMENSIONS` in `.env` to match new model's output dimension
3. **Drop and recreate** `chunk_embeddings` table (dimensions must match at column creation time)
4. Re-embed all documents (`POST /api/vector/embed` for each)

> Warning: pgvector column dimension is fixed at table creation. Changing dimensions requires a schema migration.
