from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.query_agent import query_planning_agent
from app.agents.rag_agent import graph_rag_agent
from app.db.database import get_db
from app.logger import get_logger
from app.schemas.agents import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["Query"])
logger = get_logger(__name__)


@router.post("", response_model=QueryResponse)
async def run_query(request: QueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Execute a natural language query against the knowledge graph.
    - Generates Cypher via Claude Haiku and executes it against Neo4j
    - If vector memory is available, also returns a RAG-grounded answer
    """
    logger.info("Query: %s", request.query[:120])

    # NL → Cypher → results
    cypher_result = await query_planning_agent.plan_and_execute(request.query)

    # RAG answer (best-effort — may fail if embeddings not populated)
    rag_result: dict = {"answer": None, "sources": []}
    try:
        rag_result = await graph_rag_agent.answer(request.query, db)
    except Exception as exc:
        logger.warning("RAG answer failed (non-fatal): %s", exc)

    return QueryResponse(
        query=request.query,
        cypher=cypher_result.get("cypher"),
        results=cypher_result.get("results", []),
        answer=rag_result.get("answer"),
        sources=rag_result.get("sources", []),
        error=cypher_result.get("error"),
    )
