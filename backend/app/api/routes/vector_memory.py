"""
Vector memory API routes.

POST /vector/embed-document/{document_id}  — chunk + embed a stored document
GET  /vector/search                        — semantic search over all embeddings
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.logger import get_logger
from app.schemas.vector_memory import EmbedDocumentResponse, SearchResponse, SearchResultItem
from app.vector_memory.embedding_service import embedding_service

router = APIRouter(prefix="/vector", tags=["Vector Memory"])
logger = get_logger(__name__)


@router.post(
    "/embed-document/{document_id}",
    response_model=EmbedDocumentResponse,
    summary="Chunk and embed a document",
)
async def embed_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> EmbedDocumentResponse:
    """
    Chunk the document's text, generate OpenAI embeddings for each chunk,
    and store them in pgvector.  Idempotent — re-running replaces existing embeddings.
    """
    logger.info("Embed request for document_id=%s", document_id)
    try:
        result = await embedding_service.embed_document(document_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return EmbedDocumentResponse(
        document_id=result.document_id,
        chunks_created=result.chunks_created,
        model_used=result.model_used,
        already_embedded=result.already_embedded,
    )


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over embedded chunks",
)
async def semantic_search(
    q: str = Query(..., min_length=1, description="Natural language query"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results to return"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Embed the query and return the top-k most similar document chunks,
    ranked by cosine similarity.
    """
    logger.info("Semantic search: q=%r top_k=%d", q, top_k)
    try:
        results = await embedding_service.semantic_search(q, top_k, db)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SearchResponse(
        query=q,
        top_k=top_k,
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                filename=r.filename,
                text=r.text,
                similarity_score=r.similarity_score,
                chunk_index=r.chunk_index,
                token_count=r.token_count,
                metadata=r.metadata,
            )
            for r in results
        ],
    )
