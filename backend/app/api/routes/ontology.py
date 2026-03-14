"""
Ontology routes.

Existing (in-memory manager, preserved):
  GET  /ontology/classes          — list seeded ontology classes
  POST /ontology/classes          — create a new class
  POST /ontology/align            — stub (501)

New (AI discovery + DB versioning):
  POST /ontology/generate         — run AI discovery, persist OntologyVersion
  GET  /ontology                  — list version summaries
  GET  /ontology/{version_id}     — get full ontology for a version

IMPORTANT: concrete path segments (/classes, /generate) are registered BEFORE
the parameterised route (/{version_id}) so FastAPI doesn't swallow them.
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ExtractedEntity, ExtractedRelationship, OntologyVersion
from app.logger import get_logger
from app.ontology.discovery_agent import ontology_discovery_agent
from app.ontology.manager import ontology_manager
from app.schemas.ontology import (
    AlignmentRequest,
    OntologyClassRequest,
    OntologyContent,
    OntologyGenerateRequest,
    OntologyListResponse,
    OntologyVersionDetail,
    OntologyVersionSummary,
)

router = APIRouter(prefix="/ontology", tags=["Ontology"])
logger = get_logger(__name__)


# ── Existing in-memory routes (preserved) ─────────────────────────────────────

@router.get("/classes")
async def list_classes():
    """List all ontology classes (in-memory manager)."""
    classes = ontology_manager.list_classes()
    return {
        "classes": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "parent_class": c.parent_class,
                "properties": c.properties,
            }
            for c in classes
        ],
        "total": len(classes),
    }


@router.post("/classes", status_code=201)
async def create_class(request: OntologyClassRequest):
    """Create a new ontology class (in-memory manager)."""
    try:
        cls = ontology_manager.create_class(
            name=request.name,
            description=request.description,
            parent_class=request.parent_class,
        )
        return {"id": cls.id, "name": cls.name, "description": cls.description}
    except ValueError as exc:
        return {"error": str(exc)}


@router.post("/align", status_code=501)
async def align_entities(request: AlignmentRequest):
    """Align extracted entities to ontology classes using AI (not yet implemented)."""
    logger.info("Alignment request: document_id=%s", request.document_id)
    return {"status": "not_implemented", "module": "ontology.align"}


# ── New: AI Discovery + versioned persistence ──────────────────────────────────

@router.post("/generate", response_model=OntologyVersionDetail, status_code=201)
async def generate_ontology(
    request: OntologyGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> OntologyVersionDetail:
    """
    Run AI ontology discovery on extracted entities and relationships.
    Creates a new versioned OntologyVersion row.
    """
    # Load entities
    entity_stmt = select(ExtractedEntity)
    if request.document_id:
        entity_stmt = entity_stmt.where(ExtractedEntity.document_id == request.document_id)
    entity_result = await db.execute(entity_stmt)
    entities = entity_result.scalars().all()

    if not entities:
        raise HTTPException(
            status_code=422,
            detail="No entities found. Run entity extraction first.",
        )

    # Load relationships
    rel_stmt = select(ExtractedRelationship)
    if request.document_id:
        rel_stmt = rel_stmt.where(ExtractedRelationship.document_id == request.document_id)
    rel_result = await db.execute(rel_stmt)
    relationships = rel_result.scalars().all()

    # Compute next version number (scoped per document_id, or global if None)
    if request.document_id:
        max_stmt = select(func.max(OntologyVersion.version)).where(
            OntologyVersion.document_id == request.document_id
        )
    else:
        max_stmt = select(func.max(OntologyVersion.version)).where(
            OntologyVersion.document_id.is_(None)
        )
    max_result = await db.execute(max_stmt)
    max_version = max_result.scalar() or 0
    next_version = max_version + 1

    logger.info(
        "Generating ontology v%d for document_id=%r with %d entities, %d relationships",
        next_version, request.document_id, len(entities), len(relationships),
    )

    # Run AI discovery
    try:
        ontology_dict = await ontology_discovery_agent.discover(
            list(entities),
            list(relationships),
            domain_hint=request.domain_hint,
        )
    except Exception as exc:
        logger.error("Ontology discovery failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"AI discovery failed: {exc}") from exc

    # Persist
    classes_count = len(ontology_dict.get("classes", []))
    rels_count = len(ontology_dict.get("relationships", []))

    row = OntologyVersion(
        id=str(uuid.uuid4()),
        version=next_version,
        document_id=request.document_id,
        domain_hint=request.domain_hint,
        ontology_json=json.dumps(ontology_dict),
        classes_count=classes_count,
        relationships_count=rels_count,
        model_used="claude-sonnet-4-6",
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    logger.info(
        "Persisted OntologyVersion id=%s v%d (%d classes, %d relationships)",
        row.id, row.version, classes_count, rels_count,
    )

    ontology_content = OntologyContent(**ontology_dict)
    return OntologyVersionDetail(
        id=row.id,
        version=row.version,
        document_id=row.document_id,
        domain_hint=row.domain_hint,
        classes_count=row.classes_count,
        relationships_count=row.relationships_count,
        model_used=row.model_used,
        created_at=row.created_at,
        ontology=ontology_content,
    )


@router.get("", response_model=OntologyListResponse)
async def list_ontology_versions(
    document_id: str | None = Query(default=None, description="Filter by document ID"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> OntologyListResponse:
    """List ontology version summaries, newest first."""
    stmt = select(OntologyVersion).order_by(OntologyVersion.created_at.desc())
    if document_id:
        stmt = stmt.where(OntologyVersion.document_id == document_id)
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    summaries = [
        OntologyVersionSummary(
            id=r.id,
            version=r.version,
            document_id=r.document_id,
            domain_hint=r.domain_hint,
            classes_count=r.classes_count,
            relationships_count=r.relationships_count,
            model_used=r.model_used,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return OntologyListResponse(versions=summaries, total=len(summaries))


@router.get("/{version_id}", response_model=OntologyVersionDetail)
async def get_ontology_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
) -> OntologyVersionDetail:
    """Get a specific ontology version with full content."""
    result = await db.execute(
        select(OntologyVersion).where(OntologyVersion.id == version_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"OntologyVersion {version_id!r} not found")

    ontology_dict = json.loads(row.ontology_json)
    ontology_content = OntologyContent(**ontology_dict)

    return OntologyVersionDetail(
        id=row.id,
        version=row.version,
        document_id=row.document_id,
        domain_hint=row.domain_hint,
        classes_count=row.classes_count,
        relationships_count=row.relationships_count,
        model_used=row.model_used,
        created_at=row.created_at,
        ontology=ontology_content,
    )
