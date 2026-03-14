"""
VectorEmbeddingService: chunk → embed → store, and semantic search.
"""
import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import ChunkEmbedding, Document
from app.logger import get_logger
from app.preprocessing.chunker import SlidingWindowChunker
from app.vector_memory.base import EmbedResult, SearchResult

logger = get_logger(__name__)


class VectorEmbeddingService:
    """
    Handles embedding generation for stored documents and semantic search.
    """

    def __init__(self) -> None:
        # Import lazily to avoid circular deps; client is a module-level singleton
        from app.ai.openai_client import openai_client
        self._client = openai_client
        self._chunker = SlidingWindowChunker()

    async def embed_document(self, document_id: str, db: AsyncSession) -> EmbedResult:
        """
        Chunk the document's raw_text, embed each chunk via OpenAI, and persist
        ChunkEmbedding rows.  Idempotent: deletes existing embeddings first.
        """
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ValueError(f"Document {document_id!r} not found")

        # Delete any previous embeddings so we can re-embed cleanly
        existing = await db.execute(
            select(ChunkEmbedding).where(ChunkEmbedding.document_id == document_id)
        )
        for row in existing.scalars().all():
            await db.delete(row)

        chunks = self._chunker.chunk(doc.raw_text)
        if not chunks:
            await db.commit()
            return EmbedResult(
                document_id=document_id,
                chunks_created=0,
                model_used=settings.OPENAI_EMBEDDING_MODEL,
            )

        logger.info(
            "Embedding document %s: %d chunks with model %s",
            document_id, len(chunks), settings.OPENAI_EMBEDDING_MODEL,
        )

        for chunk in chunks:
            vector = await self._client.create_embedding(
                chunk.text, model=settings.OPENAI_EMBEDDING_MODEL
            )
            meta = json.dumps({"start_char": chunk.start_char, "end_char": chunk.end_char})
            db.add(ChunkEmbedding(
                document_id=document_id,
                chunk_index=chunk.index,
                text=chunk.text,
                embedding=vector,
                token_count=chunk.token_count,
                metadata_json=meta,
            ))

        await db.commit()
        logger.info("Stored %d embeddings for document %s", len(chunks), document_id)
        return EmbedResult(
            document_id=document_id,
            chunks_created=len(chunks),
            model_used=settings.OPENAI_EMBEDDING_MODEL,
        )

    async def semantic_search(
        self, query: str, top_k: int, db: AsyncSession
    ) -> list[SearchResult]:
        """
        Embed the query and return the top-k most similar chunks using pgvector
        cosine distance.
        """
        query_vector = await self._client.create_embedding(
            query, model=settings.OPENAI_EMBEDDING_MODEL
        )

        # pgvector cosine distance: <=>  (lower = more similar)
        # Cast the python list to a pgvector literal for the query
        stmt = text(
            """
            SELECT
                ce.id,
                ce.document_id,
                d.filename,
                ce.text,
                1 - (ce.embedding <=> CAST(:qvec AS vector)) AS similarity,
                ce.chunk_index,
                ce.token_count,
                ce.metadata_json
            FROM chunk_embeddings ce
            JOIN documents d ON d.id = ce.document_id
            ORDER BY ce.embedding <=> CAST(:qvec AS vector)
            LIMIT :top_k
            """
        )

        vec_str = "[" + ",".join(str(v) for v in query_vector) + "]"
        rows = await db.execute(stmt, {"qvec": vec_str, "top_k": top_k})

        results: list[SearchResult] = []
        for row in rows.mappings():
            try:
                meta = json.loads(row["metadata_json"])
            except (json.JSONDecodeError, KeyError):
                meta = {}
            results.append(SearchResult(
                chunk_id=row["id"],
                document_id=row["document_id"],
                filename=row["filename"],
                text=row["text"],
                similarity_score=round(float(row["similarity"]), 4),
                chunk_index=row["chunk_index"],
                token_count=row["token_count"],
                metadata=meta,
            ))

        return results


# Module-level singleton
embedding_service = VectorEmbeddingService()
