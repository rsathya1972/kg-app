"""
Agentic pipeline: 5 sequential nodes that process a document end-to-end.

Pipeline:
  entity_extraction → relationship_discovery → ontology_builder
      → graph_update → vector_memory

Each node:
  1. Pushes a "step_start" SSE event
  2. Calls the appropriate service
  3. Persists results + updates the AgentRun DB row
  4. Pushes a "step_complete" / "step_failed" SSE event
  5. Returns the updated state
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

import app.agents.event_bus as event_bus
from app.agents.graph import StateGraph
from app.agents.state import PipelineState
from app.db.database import AsyncSessionLocal
from app.db.models import (
    AgentRun,
    Document,
    ExtractedEntity,
    ExtractedRelationship,
    OntologyVersion,
)
from app.extraction.base import Entity as ExEntity
from app.extraction.entity_extractor import EntityExtractionAgent
from app.extraction.relation_extractor import RelationExtractor
from app.graph.writer import graph_builder
from app.logger import get_logger
from app.ontology.discovery_agent import ontology_discovery_agent
from app.vector_memory.embedding_service import embedding_service

logger = get_logger(__name__)

_entity_agent = EntityExtractionAgent()
_rel_agent = RelationExtractor()

STEP_NAMES = [
    "entity_extraction",
    "relationship_discovery",
    "ontology_builder",
    "graph_update",
    "vector_memory",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


async def _update_run_step(
    run_id: str,
    step_name: str,
    step_status: str,
    output_summary: str | None,
    started_at: datetime,
    error: str | None = None,
) -> None:
    """Persist step result and update AgentRun row in DB."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if run is None:
            return

        steps = json.loads(run.steps_json)
        completed_at = _now_dt()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Upsert this step
        existing = next((s for s in steps if s["step_name"] == step_name), None)
        step_data = {
            "step_name": step_name,
            "status": step_status,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "output_summary": output_summary,
            "error": error,
        }
        if existing:
            existing.update(step_data)
        else:
            steps.append(step_data)

        run.steps_json = json.dumps(steps)
        run.current_step = step_name if step_status == "running" else None

        if step_status == "completed":
            # Mark next step as "pending" placeholder so frontend can show it
            pass

        await db.commit()


async def _mark_step_start(run_id: str, step_name: str) -> datetime:
    """Mark step as running in DB + push SSE event. Returns start time."""
    started_at = _now_dt()
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if run:
            steps = json.loads(run.steps_json)
            steps.append({
                "step_name": step_name,
                "status": "running",
                "started_at": started_at.isoformat(),
                "completed_at": None,
                "duration_ms": None,
                "output_summary": None,
                "error": None,
            })
            run.steps_json = json.dumps(steps)
            run.current_step = step_name
            run.status = "running"
            await db.commit()

    await event_bus.push(run_id, {
        "type": "step_start",
        "step": step_name,
        "timestamp": started_at.isoformat(),
    })
    return started_at


async def _add_decision(run_id: str, agent: str, message: str) -> dict:
    decision = {"agent": agent, "message": message, "timestamp": _now_iso()}
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if run:
            decisions = json.loads(run.decisions_json)
            decisions.append(decision)
            run.decisions_json = json.dumps(decisions)
            await db.commit()
    return decision


# ── Node implementations ───────────────────────────────────────────────────────

async def entity_extraction_node(state: PipelineState) -> PipelineState:
    step_name = "entity_extraction"
    run_id = state["run_id"]
    doc_id = state["document_id"]

    started_at = await _mark_step_start(run_id, step_name)

    try:
        # Load document text
        async with AsyncSessionLocal() as db:
            doc = await db.get(Document, doc_id)
        if doc is None:
            raise ValueError(f"Document {doc_id} not found")
        text = doc.raw_text

        # Run AI extraction
        result = await _entity_agent.extract(doc_id, text)

        # Persist entities
        entity_ids: list[str] = []
        async with AsyncSessionLocal() as db:
            for entity in result.entities:
                row = ExtractedEntity(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    entity_type=entity.label,
                    name=entity.text,
                    attributes_json=json.dumps(entity.attributes),
                    evidence_chunk=str(entity.source_chunk or ""),
                    confidence=entity.confidence or 0.0,
                )
                db.add(row)
                entity_ids.append(row.id)
            await db.commit()

        summary = f"{len(entity_ids)} entities extracted"
        await _update_run_step(run_id, step_name, "completed", summary, started_at)
        decision = await _add_decision(run_id, "EntityExtractionAgent", summary)
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": summary, "timestamp": _now_iso(),
        })

        return {
            **state,
            "document_text": text,
            "entity_ids": entity_ids,
            "decisions": state["decisions"] + [decision],
            "completed_steps": state["completed_steps"] + [step_name],
        }

    except Exception as exc:
        error_msg = str(exc)
        await _update_run_step(run_id, step_name, "failed", None, started_at, error=error_msg)
        await event_bus.push(run_id, {
            "type": "step_failed", "step": step_name,
            "error": error_msg, "timestamp": _now_iso(),
        })
        return {**state, "errors": state["errors"] + [f"{step_name}: {error_msg}"]}


async def relationship_discovery_node(state: PipelineState) -> PipelineState:
    step_name = "relationship_discovery"
    run_id = state["run_id"]
    doc_id = state["document_id"]

    # Skip if entity extraction failed
    if not state["entity_ids"]:
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": "Skipped — no entities available", "timestamp": _now_iso(),
        })
        return {**state, "completed_steps": state["completed_steps"] + [step_name]}

    started_at = await _mark_step_start(run_id, step_name)

    try:
        text = state.get("document_text") or ""

        # Load entity objects from DB to pass to extractor
        async with AsyncSessionLocal() as db:
            result_rows = await db.execute(
                select(ExtractedEntity).where(
                    ExtractedEntity.id.in_(state["entity_ids"])
                )
            )
            entity_rows = list(result_rows.scalars().all())

        # Convert DB rows back to extraction Entity dataclass for the extractor
        entities_for_extractor: list[ExEntity] = [
            ExEntity(
                id=row.id,
                text=row.name,
                label=row.entity_type,
                confidence=row.confidence,
                attributes=json.loads(row.attributes_json),
            )
            for row in entity_rows
        ]

        result = await _rel_agent.extract_from_entities(doc_id, text, entities_for_extractor)

        # Build name→id map for persisting
        name_to_id = {row.name.lower(): row.id for row in entity_rows}

        relationship_ids: list[str] = []
        async with AsyncSessionLocal() as db:
            for rel in result.relations:
                # Find source and target by their IDs (already set from entity.id)
                src_row = next((r for r in entity_rows if r.id == rel.subject_id), None)
                tgt_row = next((r for r in entity_rows if r.id == rel.object_id), None)

                row = ExtractedRelationship(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    source_entity_id=rel.subject_id,
                    target_entity_id=rel.object_id,
                    source_entity_name=src_row.name if src_row else rel.subject_id,
                    target_entity_name=tgt_row.name if tgt_row else rel.object_id,
                    relationship_type=rel.predicate,
                    confidence=rel.confidence or 0.0,
                    evidence_text=rel.evidence or "",
                )
                db.add(row)
                relationship_ids.append(row.id)
            await db.commit()

        summary = f"{len(relationship_ids)} relationships discovered"
        await _update_run_step(run_id, step_name, "completed", summary, started_at)
        decision = await _add_decision(run_id, "RelationshipDiscoveryAgent", summary)
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": summary, "timestamp": _now_iso(),
        })

        return {
            **state,
            "relationship_ids": relationship_ids,
            "decisions": state["decisions"] + [decision],
            "completed_steps": state["completed_steps"] + [step_name],
        }

    except Exception as exc:
        error_msg = str(exc)
        await _update_run_step(run_id, step_name, "failed", None, started_at, error=error_msg)
        await event_bus.push(run_id, {
            "type": "step_failed", "step": step_name,
            "error": error_msg, "timestamp": _now_iso(),
        })
        return {**state, "errors": state["errors"] + [f"{step_name}: {error_msg}"]}


async def ontology_builder_node(state: PipelineState) -> PipelineState:
    step_name = "ontology_builder"
    run_id = state["run_id"]
    doc_id = state["document_id"]

    if not state["entity_ids"]:
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": "Skipped — no entities available", "timestamp": _now_iso(),
        })
        return {**state, "completed_steps": state["completed_steps"] + [step_name]}

    started_at = await _mark_step_start(run_id, step_name)

    try:
        async with AsyncSessionLocal() as db:
            entity_result = await db.execute(
                select(ExtractedEntity).where(ExtractedEntity.document_id == doc_id)
            )
            entities = list(entity_result.scalars().all())

            rel_result = await db.execute(
                select(ExtractedRelationship).where(ExtractedRelationship.document_id == doc_id)
            )
            relationships = list(rel_result.scalars().all())

        # Compute next version number
        async with AsyncSessionLocal() as db:
            from sqlalchemy import func
            max_ver_result = await db.execute(
                select(func.max(OntologyVersion.version)).where(
                    OntologyVersion.document_id == doc_id
                )
            )
            max_ver = max_ver_result.scalar() or 0
            next_version = max_ver + 1

        ontology_dict = await ontology_discovery_agent.discover(
            entities, relationships, state.get("domain_hint")
        )

        ontology_json = json.dumps(ontology_dict)
        classes_count = len(ontology_dict.get("classes", []))
        relationships_count = len(ontology_dict.get("relationships", []))

        async with AsyncSessionLocal() as db:
            version_row = OntologyVersion(
                id=str(uuid.uuid4()),
                version=next_version,
                document_id=doc_id,
                domain_hint=state.get("domain_hint"),
                ontology_json=ontology_json,
                classes_count=classes_count,
                relationships_count=relationships_count,
                model_used="claude-sonnet-4-6",
            )
            db.add(version_row)
            await db.commit()
            version_id = version_row.id

        summary = f"Ontology v{next_version}: {classes_count} classes, {relationships_count} relationships"
        await _update_run_step(run_id, step_name, "completed", summary, started_at)
        decision = await _add_decision(run_id, "OntologyBuilderAgent", summary)
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": summary, "timestamp": _now_iso(),
        })

        return {
            **state,
            "ontology_version_id": version_id,
            "decisions": state["decisions"] + [decision],
            "completed_steps": state["completed_steps"] + [step_name],
        }

    except Exception as exc:
        error_msg = str(exc)
        await _update_run_step(run_id, step_name, "failed", None, started_at, error=error_msg)
        await event_bus.push(run_id, {
            "type": "step_failed", "step": step_name,
            "error": error_msg, "timestamp": _now_iso(),
        })
        return {**state, "errors": state["errors"] + [f"{step_name}: {error_msg}"]}


async def graph_update_node(state: PipelineState) -> PipelineState:
    step_name = "graph_update"
    run_id = state["run_id"]
    doc_id = state["document_id"]

    if not state["entity_ids"]:
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": "Skipped — no entities available", "timestamp": _now_iso(),
        })
        return {**state, "completed_steps": state["completed_steps"] + [step_name]}

    started_at = await _mark_step_start(run_id, step_name)

    try:
        async with AsyncSessionLocal() as db:
            entity_result = await db.execute(
                select(ExtractedEntity).where(ExtractedEntity.document_id == doc_id)
            )
            entities = list(entity_result.scalars().all())

            rel_result = await db.execute(
                select(ExtractedRelationship).where(
                    ExtractedRelationship.document_id == doc_id,
                    ExtractedRelationship.source_entity_id.isnot(None),
                    ExtractedRelationship.target_entity_id.isnot(None),
                )
            )
            relationships = list(rel_result.scalars().all())

        stats = await graph_builder.build(entities, relationships)

        summary = (
            f"{stats['nodes_created']} nodes created, {stats['edges_created']} edges created, "
            f"{stats['nodes_updated']} updated"
        )
        await _update_run_step(run_id, step_name, "completed", summary, started_at)
        decision = await _add_decision(run_id, "GraphUpdateAgent", summary)
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": summary, "timestamp": _now_iso(),
        })

        return {
            **state,
            "graph_stats": stats,
            "decisions": state["decisions"] + [decision],
            "completed_steps": state["completed_steps"] + [step_name],
        }

    except Exception as exc:
        error_msg = str(exc)
        await _update_run_step(run_id, step_name, "failed", None, started_at, error=error_msg)
        await event_bus.push(run_id, {
            "type": "step_failed", "step": step_name,
            "error": error_msg, "timestamp": _now_iso(),
        })
        return {**state, "errors": state["errors"] + [f"{step_name}: {error_msg}"]}


async def vector_memory_node(state: PipelineState) -> PipelineState:
    step_name = "vector_memory"
    run_id = state["run_id"]
    doc_id = state["document_id"]

    started_at = await _mark_step_start(run_id, step_name)

    try:
        async with AsyncSessionLocal() as db:
            embed_result = await embedding_service.embed_document(doc_id, db)

        summary = f"{embed_result.chunks_created} chunks embedded (model: {embed_result.model_used})"
        await _update_run_step(run_id, step_name, "completed", summary, started_at)
        decision = await _add_decision(run_id, "VectorMemoryAgent", summary)
        await event_bus.push(run_id, {
            "type": "step_complete", "step": step_name,
            "summary": summary, "timestamp": _now_iso(),
        })

        return {
            **state,
            "embed_result": {
                "chunks_created": embed_result.chunks_created,
                "model_used": embed_result.model_used,
            },
            "decisions": state["decisions"] + [decision],
            "completed_steps": state["completed_steps"] + [step_name],
        }

    except Exception as exc:
        error_msg = str(exc)
        await _update_run_step(run_id, step_name, "failed", None, started_at, error=error_msg)
        await event_bus.push(run_id, {
            "type": "step_failed", "step": step_name,
            "error": error_msg, "timestamp": _now_iso(),
        })
        return {**state, "errors": state["errors"] + [f"{step_name}: {error_msg}"]}


# ── Compile the graph ──────────────────────────────────────────────────────────

_g = StateGraph(PipelineState)
_g.add_node("entity_extraction", entity_extraction_node)
_g.add_node("relationship_discovery", relationship_discovery_node)
_g.add_node("ontology_builder", ontology_builder_node)
_g.add_node("graph_update", graph_update_node)
_g.add_node("vector_memory", vector_memory_node)
_g.add_edge("entity_extraction", "relationship_discovery")
_g.add_edge("relationship_discovery", "ontology_builder")
_g.add_edge("ontology_builder", "graph_update")
_g.add_edge("graph_update", "vector_memory")
_g.set_entry_point("entity_extraction")

pipeline_graph = _g.compile()


async def run_pipeline(run_id: str, document_id: str, domain_hint: str | None = None) -> None:
    """
    Top-level coroutine: initialise state, invoke graph, finalise run.
    Called as a background task from the API route.
    """
    initial_state: PipelineState = {
        "run_id": run_id,
        "document_id": document_id,
        "document_text": None,
        "domain_hint": domain_hint,
        "entity_ids": [],
        "relationship_ids": [],
        "ontology_version_id": None,
        "graph_stats": None,
        "embed_result": None,
        "errors": [],
        "decisions": [],
        "completed_steps": [],
    }

    try:
        final_state = await pipeline_graph.ainvoke(initial_state)
        has_errors = bool(final_state.get("errors"))
        final_status = "failed" if has_errors else "completed"
        error_message = "; ".join(final_state["errors"]) if has_errors else None

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.status = final_status
                run.current_step = None
                run.completed_at = _now_dt()
                run.error_message = error_message
                await db.commit()

        await event_bus.push(run_id, {
            "type": "run_complete" if not has_errors else "run_failed",
            "status": final_status,
            "timestamp": _now_iso(),
            "error": error_message,
        })

    except Exception as exc:
        logger.exception("Pipeline crashed for run %s: %s", run_id, exc)
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.current_step = None
                run.completed_at = _now_dt()
                run.error_message = str(exc)
                await db.commit()

        await event_bus.push(run_id, {
            "type": "run_failed",
            "error": str(exc),
            "timestamp": _now_iso(),
        })
    finally:
        # Give SSE consumer a moment to drain the final event, then close
        import asyncio
        await asyncio.sleep(2)
        event_bus.close(run_id)
