"""
Relationship extraction and retrieval routes.

POST /relationships/extract/{document_id}  — run AI relation extraction on a document
GET  /relationships                         — list extracted relationships (with filters)
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, ExtractedEntity, ExtractedRelationship
from app.extraction.base import Entity
from app.extraction.relation_extractor import RelationExtractor
from app.logger import get_logger
from app.schemas.extraction import RelationshipListResponse, RelationshipResponse

router = APIRouter(prefix="/relationships", tags=["Relationships"])
logger = get_logger(__name__)


def _rel_to_response(r: ExtractedRelationship) -> RelationshipResponse:
    return RelationshipResponse(
        id=r.id,
        document_id=r.document_id,
        source_entity_id=r.source_entity_id,
        target_entity_id=r.target_entity_id,
        source_entity_name=r.source_entity_name,
        target_entity_name=r.target_entity_name,
        relationship_type=r.relationship_type,
        confidence=r.confidence,
        evidence_text=r.evidence_text,
        created_at=r.created_at,
    )


def _db_entity_to_domain(e: ExtractedEntity) -> Entity:
    """Convert ORM ExtractedEntity to extraction domain Entity."""
    try:
        attributes = json.loads(e.attributes_json)
    except (json.JSONDecodeError, TypeError):
        attributes = {}
    return Entity(
        id=e.id,
        text=e.name,
        label=e.entity_type,
        confidence=e.confidence,
        attributes=attributes,
    )


@router.post("/extract/{document_id}", response_model=RelationshipListResponse, status_code=200)
async def extract_relationships(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> RelationshipListResponse:
    """
    Run AI relationship extraction on an ingested document.
    Requires entity extraction to have been run first.
    Re-running replaces any previously extracted relationships.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id!r} not found")

    entity_result = await db.execute(
        select(ExtractedEntity).where(ExtractedEntity.document_id == document_id)
    )
    db_entities = entity_result.scalars().all()
    if not db_entities:
        raise HTTPException(
            status_code=422,
            detail="No entities found for this document. Run entity extraction first.",
        )

    # Fresh start — delete stale relationships
    await db.execute(
        delete(ExtractedRelationship).where(ExtractedRelationship.document_id == document_id)
    )
    await db.flush()

    # Build entity id → name lookup for resolving relation endpoints
    domain_entities = [_db_entity_to_domain(e) for e in db_entities]
    entity_id_to_name: dict[str, str] = {e.id: e.text for e in domain_entities}

    extractor = RelationExtractor()
    extraction = await extractor.extract_from_entities(document_id, doc.raw_text, domain_entities)

    now = datetime.now(timezone.utc)
    db_rels: list[ExtractedRelationship] = []

    for rel in extraction.relations:
        source_name = entity_id_to_name.get(rel.subject_id, rel.subject_id)
        target_name = entity_id_to_name.get(rel.object_id, rel.object_id)

        db_rel = ExtractedRelationship(
            id=str(uuid.uuid4()),
            document_id=document_id,
            source_entity_id=rel.subject_id,
            target_entity_id=rel.object_id,
            source_entity_name=source_name,
            target_entity_name=target_name,
            relationship_type=rel.predicate,
            confidence=rel.confidence or 0.0,
            evidence_text=rel.evidence or "",
            created_at=now,
        )
        db.add(db_rel)
        db_rels.append(db_rel)

    await db.commit()

    logger.info(
        "Persisted %d relationships for document_id=%s", len(db_rels), document_id
    )

    responses = [_rel_to_response(r) for r in db_rels]
    return RelationshipListResponse(relationships=responses, total=len(responses))


@router.get("", response_model=RelationshipListResponse)
async def list_relationships(
    document_id: str | None = Query(default=None, description="Filter by document ID"),
    relationship_type: str | None = Query(default=None, description="Filter by relationship type"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> RelationshipListResponse:
    """List extracted relationships with optional filters."""
    stmt = select(ExtractedRelationship).order_by(ExtractedRelationship.created_at.desc())

    if document_id:
        stmt = stmt.where(ExtractedRelationship.document_id == document_id)
    if relationship_type:
        stmt = stmt.where(ExtractedRelationship.relationship_type == relationship_type)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rels = result.scalars().all()

    responses = [_rel_to_response(r) for r in rels]
    return RelationshipListResponse(relationships=responses, total=len(responses))
