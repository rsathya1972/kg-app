from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import KnowledgeIssue, OntologyProposal
from app.learning.engine import knowledge_evolution_engine
from app.logger import get_logger
from app.schemas.learning import (
    AnalysisResult,
    EvaluationMetrics,
    IssueListResponse,
    KnowledgeIssueResponse,
    OntologyProposalResponse,
    ProposalListResponse,
    TriggerAnalysisRequest,
)

router = APIRouter(prefix="/learning", tags=["Learning"])
logger = get_logger(__name__)


@router.post("/analyze", response_model=AnalysisResult)
async def trigger_analysis(
    request: TriggerAnalysisRequest, db: AsyncSession = Depends(get_db)
):
    """
    Run the full Knowledge Evolution Engine pipeline:
      1. Detect quality issues (low confidence, duplicates, orphans, unknown types)
      2. Generate AI-driven ontology change proposals
      3. Optionally auto-correct duplicates and type normalization
      4. Compute and return evaluation metrics

    Set `auto_correct=true` to apply safe auto-corrections automatically.
    """
    logger.info(
        "Knowledge analysis triggered (auto_correct=%s, threshold=%.2f)",
        request.auto_correct,
        request.confidence_threshold,
    )
    return await knowledge_evolution_engine.analyze(
        db,
        auto_correct=request.auto_correct,
        threshold=request.confidence_threshold,
    )


@router.get("/metrics", response_model=EvaluationMetrics)
async def get_metrics(
    threshold: float = Query(default=0.5, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute and return current knowledge graph evaluation metrics without
    running the full analysis pipeline.
    """
    return await knowledge_evolution_engine.compute_metrics(db, threshold)


@router.get("/issues", response_model=IssueListResponse)
async def list_issues(
    issue_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str = Query(default="open"),
    db: AsyncSession = Depends(get_db),
):
    """List detected knowledge graph issues with optional filters."""
    stmt = select(KnowledgeIssue).where(KnowledgeIssue.status == status)
    if issue_type:
        stmt = stmt.where(KnowledgeIssue.issue_type == issue_type)
    if severity:
        stmt = stmt.where(KnowledgeIssue.severity == severity)
    stmt = stmt.order_by(KnowledgeIssue.detected_at.desc())

    rows = (await db.execute(stmt)).scalars().all()

    issues = []
    for row in rows:
        issues.append(KnowledgeIssueResponse(
            id=row.id,
            issue_type=row.issue_type,
            severity=row.severity,
            entity_id=row.entity_id,
            relationship_id=row.relationship_id,
            document_id=row.document_id,
            description=row.description,
            detail=row.detail_json,  # field_validator handles str→dict
            status=row.status,
            detected_at=row.detected_at,
        ))

    return IssueListResponse(issues=issues, total=len(issues))


@router.get("/proposals", response_model=ProposalListResponse)
async def list_proposals(
    status: str = Query(default="pending"),
    db: AsyncSession = Depends(get_db),
):
    """List ontology evolution proposals."""
    stmt = (
        select(OntologyProposal)
        .where(OntologyProposal.status == status)
        .order_by(OntologyProposal.proposed_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    proposals = []
    for row in rows:
        proposals.append(OntologyProposalResponse(
            id=row.id,
            proposal_type=row.proposal_type,
            status=row.status,
            description=row.description,
            rationale=row.rationale,
            detail=row.detail_json,
            proposed_at=row.proposed_at,
            applied_at=row.applied_at,
        ))

    return ProposalListResponse(proposals=proposals, total=len(proposals))


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str, db: AsyncSession = Depends(get_db)):
    """
    Apply a pending ontology proposal.
    For `add_class` proposals: registers the class in the active ontology manager.
    For other types: marks as applied and notes that a graph rebuild may be needed.
    """
    success, message = await knowledge_evolution_engine.apply_proposal(proposal_id, db)
    if not success and "not found" in message.lower():
        raise HTTPException(status_code=404, detail=message)
    return {"success": success, "message": message}


@router.post("/proposals/{proposal_id}/dismiss")
async def dismiss_proposal(proposal_id: str, db: AsyncSession = Depends(get_db)):
    """Dismiss a pending ontology proposal."""
    success = await knowledge_evolution_engine.dismiss_proposal(proposal_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {"success": True}
