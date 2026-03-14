"""
GraphRAGAgent: combines vector semantic search with graph neighborhood context
for grounded question answering.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anthropic_client import anthropic_client
from app.logger import get_logger
from app.vector_memory.embedding_service import embedding_service

logger = get_logger(__name__)

MODEL = "claude-sonnet-4-6"

ANSWER_SYSTEM = """\
You are a helpful assistant that answers questions using ONLY the provided document context.
Be concise, factual, and cite which source document your answer comes from.
If the context does not contain enough information to answer, say so clearly.
NEVER fabricate facts not present in the context."""


class GraphRAGAgent:
    """
    Retrieval-Augmented Generation combining vector search and graph context.

    Pipeline:
      1. Semantic search → top-K relevant chunks
      2. Combine chunks into context
      3. Ask Claude Sonnet for a grounded answer
    """

    async def answer(
        self,
        question: str,
        db: AsyncSession,
        top_k: int = 5,
    ) -> dict:
        """
        Answer a question using vector-retrieved document context.

        Returns:
            {answer, sources: [{chunk, filename, similarity}], error?}
        """
        try:
            search_results = await embedding_service.semantic_search(question, top_k, db)
        except Exception as exc:
            logger.error("Semantic search failed: %s", exc)
            return {"answer": None, "sources": [], "error": str(exc)}

        if not search_results:
            return {
                "answer": "No relevant documents found in the knowledge base for this question.",
                "sources": [],
                "error": None,
            }

        context_parts = []
        sources = []
        for result in search_results:
            context_parts.append(
                f"[Source: {result.filename} | similarity: {result.similarity_score:.2f}]\n{result.text}"
            )
            sources.append({
                "chunk": result.text[:300],
                "filename": result.filename,
                "similarity": round(result.similarity_score, 4),
                "chunk_index": result.chunk_index,
            })

        context = "\n\n---\n\n".join(context_parts)
        prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

        try:
            answer = await anthropic_client.complete(
                prompt,
                model=MODEL,
                max_tokens=1024,
                system=ANSWER_SYSTEM,
            )
        except Exception as exc:
            logger.error("Claude API error in RAG answer: %s", exc)
            return {"answer": None, "sources": sources, "error": str(exc)}

        return {"answer": answer, "sources": sources, "error": None}


graph_rag_agent = GraphRAGAgent()
