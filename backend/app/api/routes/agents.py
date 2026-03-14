"""
Agent orchestration API routes.

POST /agents/run/{document_id}    — trigger pipeline, return run_id
GET  /agents/runs                 — list runs
GET  /agents/runs/{run_id}        — run detail
GET  /agents/runs/{run_id}/stream — SSE stream of real-time events
"""
import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.agents.event_bus as event_bus
from app.agents.pipeline import run_pipeline
from app.db.database import get_db
from app.db.models import AgentRun, Document
from app.logger import get_logger
from app.schemas.agents import (
    AgentDecision,
    AgentRunDetail,
    AgentRunListResponse,
    AgentRunSummary,
    StepResult,
    TriggerRunRequest,
    TriggerRunResponse,
)

router = APIRouter(prefix="/agents", tags=["Agents"])
logger = get_logger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

STEP_NAMES = [
    "entity_extraction",
    "relationship_discovery",
    "ontology_builder",
    "graph_update",
    "vector_memory",
]


def _parse_steps(steps_json: str) -> list[StepResult]:
    try:
        raw = json.loads(steps_json)
    except Exception:
        raw = []
    return [StepResult(**s) for s in raw]


def _parse_decisions(decisions_json: str) -> list[AgentDecision]:
    try:
        raw = json.loads(decisions_json)
    except Exception:
        raw = []
    results = []
    for d in raw:
        try:
            results.append(AgentDecision(**d))
        except Exception:
            pass
    return results


def _run_to_summary(run: AgentRun, doc_name: str | None) -> AgentRunSummary:
    steps = _parse_steps(run.steps_json)
    completed = sum(1 for s in steps if s.status == "completed")
    return AgentRunSummary(
        id=run.id,
        document_id=run.document_id,
        document_name=doc_name,
        status=run.status,
        current_step=run.current_step,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        steps_count=len(STEP_NAMES),
        completed_steps_count=completed,
    )


def _run_to_detail(run: AgentRun, doc_name: str | None) -> AgentRunDetail:
    steps = _parse_steps(run.steps_json)
    decisions = _parse_decisions(run.decisions_json)
    summary = _run_to_summary(run, doc_name)
    return AgentRunDetail(
        **summary.model_dump(),
        steps=steps,
        decisions=decisions,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/run/{document_id}", response_model=TriggerRunResponse, status_code=202)
async def trigger_pipeline(
    document_id: str,
    body: TriggerRunRequest = TriggerRunRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the full AI pipeline for a document.
    Returns immediately with run_id; pipeline runs in background.
    """
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    run_id = str(uuid.uuid4())
    run = AgentRun(
        id=run_id,
        document_id=document_id,
        status="pending",
        steps_json="[]",
        decisions_json="[]",
    )
    db.add(run)
    await db.commit()

    # Create SSE queue before launching task so stream endpoint can find it immediately
    event_bus.create(run_id)

    # Launch pipeline as a background asyncio task
    asyncio.create_task(
        run_pipeline(run_id, document_id, body.domain_hint),
        name=f"pipeline-{run_id}",
    )

    logger.info("Pipeline triggered: run_id=%s document_id=%s", run_id, document_id)
    return TriggerRunResponse(run_id=run_id, status="pending")


@router.get("/runs", response_model=AgentRunListResponse)
async def list_runs(
    document_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List agent runs, most recent first."""
    q = select(AgentRun).order_by(desc(AgentRun.started_at))
    if document_id:
        q = q.where(AgentRun.document_id == document_id)
    if status:
        q = q.where(AgentRun.status == status)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    runs = list(result.scalars().all())

    # Batch-load document names
    doc_ids = {r.document_id for r in runs if r.document_id}
    doc_names: dict[str, str] = {}
    if doc_ids:
        doc_result = await db.execute(select(Document).where(Document.id.in_(doc_ids)))
        for doc in doc_result.scalars().all():
            doc_names[doc.id] = doc.filename

    summaries = [_run_to_summary(r, doc_names.get(r.document_id or "")) for r in runs]

    # Count total
    from sqlalchemy import func
    count_q = select(func.count(AgentRun.id))
    if document_id:
        count_q = count_q.where(AgentRun.document_id == document_id)
    if status:
        count_q = count_q.where(AgentRun.status == status)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    return AgentRunListResponse(runs=summaries, total=total)


@router.get("/runs/{run_id}", response_model=AgentRunDetail)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Get full detail for a single agent run."""
    run = await db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    doc_name: str | None = None
    if run.document_id:
        doc = await db.get(Document, run.document_id)
        if doc:
            doc_name = doc.filename

    return _run_to_detail(run, doc_name)


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    """
    SSE stream for a running pipeline.
    Sends events as: data: {json}\n\n
    Closes when run_complete or run_failed event is received, or after timeout.
    """
    async def generate():
        queue = event_bus.get(run_id)
        if queue is None:
            # Already completed — send done immediately
            yield 'data: {"type":"done"}\n\n'
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield 'data: {"type":"ping"}\n\n'
                continue

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") in ("run_complete", "run_failed", "done"):
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
