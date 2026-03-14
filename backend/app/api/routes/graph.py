from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ExtractedEntity, ExtractedRelationship
from app.graph.writer import graph_builder
from app.graph.reader import graph_reader
from app.schemas.graph import GraphResponse, GraphWriteResponse, NodeResponse, EdgeResponse
from app.logger import get_logger

router = APIRouter(prefix="/graph", tags=["Graph"])
logger = get_logger(__name__)


def _neo4j_unavailable(exc: RuntimeError) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Neo4j not available. Start Neo4j and restart the backend.",
    )


@router.post("/build/{document_id}", response_model=GraphWriteResponse)
async def build_graph(document_id: str, db: AsyncSession = Depends(get_db)):
    """
    Build (or rebuild) the knowledge graph for a document.
    Loads extracted entities and relationships from PostgreSQL and MERGEs them into Neo4j.
    """
    entity_result = await db.execute(
        select(ExtractedEntity).where(ExtractedEntity.document_id == document_id)
    )
    entities = list(entity_result.scalars().all())

    if not entities:
        raise HTTPException(
            status_code=422,
            detail="No entities found for this document. Run entity extraction first.",
        )

    rel_result = await db.execute(
        select(ExtractedRelationship).where(
            ExtractedRelationship.document_id == document_id,
            ExtractedRelationship.source_entity_id.isnot(None),
            ExtractedRelationship.target_entity_id.isnot(None),
        )
    )
    relationships = list(rel_result.scalars().all())

    logger.info(
        "Building graph for document %s: %d entities, %d relationships",
        document_id, len(entities), len(relationships),
    )

    try:
        counts = await graph_builder.build(entities, relationships)
    except RuntimeError as exc:
        raise _neo4j_unavailable(exc)

    return GraphWriteResponse(**counts)


@router.get("/document/{document_id}", response_model=GraphResponse)
async def get_document_graph(document_id: str):
    """Return all nodes and edges for a document."""
    try:
        data = await graph_reader.get_document_graph(document_id)
    except RuntimeError as exc:
        raise _neo4j_unavailable(exc)

    nodes = [
        NodeResponse(id=n["id"], labels=n["labels"], properties=n["properties"])
        for n in data["nodes"]
    ]
    edges = [
        EdgeResponse(
            id=e["id"],
            type=e["type"],
            source_id=e["source_id"],
            target_id=e["target_id"],
            properties=e.get("properties"),
        )
        for e in data["edges"]
    ]
    return GraphResponse(
        nodes=nodes,
        edges=edges,
        node_count=data["node_count"],
        edge_count=data["edge_count"],
    )


@router.get("/neighborhood/{entity_id}", response_model=GraphResponse)
async def get_neighborhood(entity_id: str, depth: int = 2):
    """Return nodes and edges within `depth` hops of the given entity (pg_id)."""
    try:
        data = await graph_reader.get_neighborhood(entity_id, depth)
    except RuntimeError as exc:
        raise _neo4j_unavailable(exc)

    nodes = [
        NodeResponse(id=n["id"], labels=n["labels"], properties=n["properties"])
        for n in data["nodes"]
        if n.get("id")
    ]
    edges = [
        EdgeResponse(
            id=e["id"],
            type=e["type"],
            source_id=e["source_id"],
            target_id=e["target_id"],
        )
        for e in data["edges"]
        if e.get("source_id") and e.get("target_id")
    ]
    return GraphResponse(
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


@router.get("/stats")
async def get_graph_stats():
    """Return graph statistics: node count, edge count, label distribution."""
    try:
        return await graph_reader.get_stats()
    except RuntimeError as exc:
        raise _neo4j_unavailable(exc)
