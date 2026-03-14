from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.graphrag.service import graphrag_service
from app.logger import get_logger
from app.schemas.graphrag import GraphRAGRequest, GraphRAGResponse

router = APIRouter(prefix="/query", tags=["GraphRAG"])
logger = get_logger(__name__)


@router.post("/graphrag", response_model=GraphRAGResponse)
async def run_graphrag(
    request: GraphRAGRequest, db: AsyncSession = Depends(get_db)
):
    """
    Graph-RAG retrieval combining ontology reasoning, graph traversal, and vector search.

    Pipeline:
      1. Identify relevant ontology classes from the question
      2. Traverse Neo4j graph for matching entity nodes + neighborhood
      3. Perform pgvector semantic search over document chunks
      4. Synthesize a grounded answer with Claude Sonnet

    Returns the answer, full reasoning trace, retrieved graph nodes/edges,
    and the source document chunks used.
    """
    logger.info("GraphRAG query: %s", request.question[:120])
    return await graphrag_service.query(
        question=request.question,
        top_k=request.top_k,
        max_hops=request.max_hops,
        db=db,
    )
