"""
Entity extraction and retrieval routes.

POST /entities/extract/{document_id}  — run AI extraction on a document
GET  /entities                         — list extracted entities (with filters)
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, ExtractedEntity
from app.extraction.entity_extractor import EntityExtractionAgent
from app.logger import get_logger
from app.schemas.extraction import EntityListResponse, EntityResponse

router = APIRouter(prefix="/entities", tags=["Entities"])
logger = get_logger(__name__)


def _entity_to_response(e: ExtractedEntity) -> EntityResponse:
    try:
        attributes = json.loads(e.attributes_json)
    except (json.JSONDecodeError, TypeError):
        attributes = {}

    # Pull evidence out of attributes (stored there by the extractor)
    evidence = attributes.pop("_evidence", e.evidence_chunk)

    return EntityResponse(
        id=e.id,
        document_id=e.document_id,
        entity_type=e.entity_type,
        name=e.name,
        attributes=attributes,
        evidence_chunk=evidence,
        confidence=e.confidence,
        created_at=e.created_at,
    )


@router.post("/extract/{document_id}", response_model=EntityListResponse, status_code=200)
async def extract_entities(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> EntityListResponse:
    """
    Run AI entity extraction on an ingested document.
    Re-running replaces any previously extracted entities for that document.
    """
    # Verify document exists
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id!r} not found")

    # Delete existing entities for a clean re-extraction
    await db.execute(
        delete(ExtractedEntity).where(ExtractedEntity.document_id == document_id)
    )
    await db.flush()

    # Run extraction
    agent = EntityExtractionAgent()
    extraction = await agent.extract(document_id, doc.raw_text)

    # Persist results
    now = datetime.now(timezone.utc)
    db_entities: list[ExtractedEntity] = []
    for entity in extraction.entities:
        attributes = dict(entity.attributes)
        evidence = attributes.pop("_evidence", "")

        db_entity = ExtractedEntity(
            id=str(uuid.uuid4()),
            document_id=document_id,
            entity_type=entity.label,
            name=entity.text,
            attributes_json=json.dumps(attributes),
            evidence_chunk=evidence,
            confidence=entity.confidence or 0.0,
            created_at=now,
        )
        db.add(db_entity)
        db_entities.append(db_entity)

    await db.commit()

    logger.info(
        "Persisted %d entities for document_id=%s", len(db_entities), document_id
    )

    responses = [_entity_to_response(e) for e in db_entities]
    return EntityListResponse(entities=responses, total=len(responses))


@router.get("", response_model=EntityListResponse)
async def list_entities(
    document_id: str | None = Query(default=None, description="Filter by document ID"),
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> EntityListResponse:
    """List extracted entities with optional filters."""
    stmt = select(ExtractedEntity).order_by(ExtractedEntity.created_at.desc())

    if document_id:
        stmt = stmt.where(ExtractedEntity.document_id == document_id)
    if entity_type:
        stmt = stmt.where(ExtractedEntity.entity_type == entity_type)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    entities = result.scalars().all()

    responses = [_entity_to_response(e) for e in entities]
    return EntityListResponse(entities=responses, total=len(responses))
