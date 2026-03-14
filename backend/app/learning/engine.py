"""
KnowledgeEvolutionEngine: continuously analyses the knowledge graph for quality
issues, proposes ontology evolution based on real extracted data, and
auto-corrects obvious inconsistencies.

Pipeline (triggered on demand via POST /learning/analyze):
  1. detect_issues    — scan for low-confidence, duplicates, orphans, unknowns
  2. generate_proposals — Claude-driven ontology change proposals
  3. auto_correct     — delete duplicates, normalize entity_type casing
  4. compute_metrics  — compute evaluation metrics (read-only)
"""
import json
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anthropic_client import anthropic_client
from app.db.models import (
    ExtractedEntity,
    ExtractedRelationship,
    KnowledgeIssue,
    OntologyProposal,
    OntologyVersion,
)
from app.extraction.base import ENTITY_TYPES, RELATIONSHIP_TYPES
from app.graph.reader import graph_reader
from app.logger import get_logger
from app.ontology.manager import ontology_manager
from app.schemas.learning import AnalysisResult, EvaluationMetrics

logger = get_logger(__name__)

# Mutable extension for relationship types added at runtime via proposals
# (Cannot mutate the frozenset from extraction.base)
_EXTENDED_RELATIONSHIP_TYPES: dict[str, str] = {}

_MAX_ISSUE_ROWS = 200   # cap per issue type to avoid massive inserts


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeEvolutionEngine:

    # ── Metrics ───────────────────────────────────────────────────────────────

    async def compute_metrics(
        self, db: AsyncSession, threshold: float = 0.5
    ) -> EvaluationMetrics:
        """Read-only pass: compute all evaluation metrics from DB + Neo4j."""

        # Total counts
        total_entities = await db.scalar(select(func.count(ExtractedEntity.id))) or 0
        total_rels = await db.scalar(select(func.count(ExtractedRelationship.id))) or 0

        # High-confidence counts
        high_conf_e = await db.scalar(
            select(func.count(ExtractedEntity.id))
            .where(ExtractedEntity.confidence >= threshold)
        ) or 0
        high_conf_r = await db.scalar(
            select(func.count(ExtractedRelationship.id))
            .where(ExtractedRelationship.confidence >= threshold)
        ) or 0

        entity_accuracy = high_conf_e / total_entities if total_entities else 0.0
        rel_accuracy = high_conf_r / total_rels if total_rels else 0.0

        # Ontology coverage: unique entity types vs known ontology class names
        type_rows = (
            await db.execute(select(ExtractedEntity.entity_type).distinct())
        ).scalars().all()
        unique_types = [t for t in type_rows if t]
        known_names = {c.name.lower() for c in ontology_manager.list_classes()}
        covered = sum(1 for t in unique_types if t.lower() in known_names)
        ontology_coverage = covered / len(unique_types) if unique_types else 0.0

        # graph_completeness = avg relationships per entity
        graph_completeness = total_rels / max(total_entities, 1)

        # Duplicate entity groups (same name + document_id, count > 1)
        dup_count = await db.scalar(
            select(func.count()).select_from(
                select(ExtractedEntity.name, ExtractedEntity.document_id)
                .group_by(ExtractedEntity.name, ExtractedEntity.document_id)
                .having(func.count(ExtractedEntity.id) > 1)
                .subquery()
            )
        ) or 0

        # Orphan entities: not referenced in any relationship (UNION subquery)
        ref_subq = (
            select(ExtractedRelationship.source_entity_id.label("eid"))
            .where(ExtractedRelationship.source_entity_id.isnot(None))
            .union(
                select(ExtractedRelationship.target_entity_id.label("eid"))
                .where(ExtractedRelationship.target_entity_id.isnot(None))
            )
        ).subquery()
        orphan_count = await db.scalar(
            select(func.count(ExtractedEntity.id))
            .where(ExtractedEntity.id.not_in(select(ref_subq.c.eid)))
        ) or 0

        # Neo4j stats (best-effort)
        neo4j_nodes, neo4j_edges = 0, 0
        try:
            stats = await graph_reader.get_stats()
            neo4j_nodes = stats.get("node_count", 0)
            neo4j_edges = stats.get("edge_count", 0)
        except Exception:
            pass

        return EvaluationMetrics(
            entity_count=total_entities,
            relationship_count=total_rels,
            entity_accuracy=round(entity_accuracy, 4),
            relationship_accuracy=round(rel_accuracy, 4),
            ontology_coverage=round(ontology_coverage, 4),
            graph_completeness=round(graph_completeness, 4),
            low_confidence_entities=total_entities - high_conf_e,
            low_confidence_relationships=total_rels - high_conf_r,
            duplicate_entities=dup_count,
            orphan_entities=orphan_count,
            unique_entity_types=len(unique_types),
            ontology_class_count=len(ontology_manager.list_classes()),
            neo4j_node_count=neo4j_nodes,
            neo4j_edge_count=neo4j_edges,
        )

    # ── Issue Detection ───────────────────────────────────────────────────────

    async def detect_issues(
        self, db: AsyncSession, threshold: float = 0.5
    ) -> list[KnowledgeIssue]:
        """
        Fresh scan: delete open issues then create new ones for all 6 issue types.
        """
        # Clear previous open issues for a clean re-scan
        await db.execute(delete(KnowledgeIssue).where(KnowledgeIssue.status == "open"))
        await db.flush()

        issues: list[KnowledgeIssue] = []
        now = datetime.now(timezone.utc)

        # 1 — low_confidence_entity
        low_e = (await db.execute(
            select(ExtractedEntity)
            .where(ExtractedEntity.confidence < threshold)
            .order_by(ExtractedEntity.confidence)
            .limit(_MAX_ISSUE_ROWS)
        )).scalars().all()
        for e in low_e:
            issues.append(KnowledgeIssue(
                id=str(uuid.uuid4()),
                issue_type="low_confidence_entity",
                severity="warning",
                entity_id=e.id,
                document_id=e.document_id,
                description=(
                    f"Entity '{e.name}' ({e.entity_type}) has confidence "
                    f"{e.confidence:.2f}, below threshold {threshold}"
                ),
                detail_json=json.dumps({
                    "entity_name": e.name,
                    "entity_type": e.entity_type,
                    "confidence": e.confidence,
                }),
                detected_at=now,
            ))

        # 2 — low_confidence_relationship
        low_r = (await db.execute(
            select(ExtractedRelationship)
            .where(ExtractedRelationship.confidence < threshold)
            .order_by(ExtractedRelationship.confidence)
            .limit(_MAX_ISSUE_ROWS)
        )).scalars().all()
        for r in low_r:
            issues.append(KnowledgeIssue(
                id=str(uuid.uuid4()),
                issue_type="low_confidence_relationship",
                severity="warning",
                relationship_id=r.id,
                document_id=r.document_id,
                description=(
                    f"Relationship '{r.source_entity_name}' "
                    f"-[{r.relationship_type}]-> '{r.target_entity_name}' "
                    f"has confidence {r.confidence:.2f}"
                ),
                detail_json=json.dumps({
                    "source": r.source_entity_name,
                    "target": r.target_entity_name,
                    "type": r.relationship_type,
                    "confidence": r.confidence,
                }),
                detected_at=now,
            ))

        # 3 — duplicate_entity (same name + document_id, count > 1)
        dup_rows = (await db.execute(
            select(
                ExtractedEntity.name,
                ExtractedEntity.document_id,
                func.count(ExtractedEntity.id).label("cnt"),
            )
            .group_by(ExtractedEntity.name, ExtractedEntity.document_id)
            .having(func.count(ExtractedEntity.id) > 1)
            .limit(_MAX_ISSUE_ROWS)
        )).all()
        for row in dup_rows:
            issues.append(KnowledgeIssue(
                id=str(uuid.uuid4()),
                issue_type="duplicate_entity",
                severity="error",
                document_id=row.document_id,
                description=(
                    f"Entity '{row.name}' appears {row.cnt} times "
                    f"in document {(row.document_id or '')[:8]}…"
                ),
                detail_json=json.dumps({
                    "entity_name": row.name,
                    "document_id": row.document_id,
                    "count": row.cnt,
                }),
                detected_at=now,
            ))

        # 4 — orphan_entity (no relationships)
        ref_subq = (
            select(ExtractedRelationship.source_entity_id.label("eid"))
            .where(ExtractedRelationship.source_entity_id.isnot(None))
            .union(
                select(ExtractedRelationship.target_entity_id.label("eid"))
                .where(ExtractedRelationship.target_entity_id.isnot(None))
            )
        ).subquery()
        orphan_e = (await db.execute(
            select(ExtractedEntity)
            .where(ExtractedEntity.id.not_in(select(ref_subq.c.eid)))
            .limit(100)
        )).scalars().all()
        for e in orphan_e:
            issues.append(KnowledgeIssue(
                id=str(uuid.uuid4()),
                issue_type="orphan_entity",
                severity="info",
                entity_id=e.id,
                document_id=e.document_id,
                description=f"Entity '{e.name}' ({e.entity_type}) has no relationships",
                detail_json=json.dumps({
                    "entity_name": e.name,
                    "entity_type": e.entity_type,
                }),
                detected_at=now,
            ))

        # 5 — unknown_entity_type (not in base ENTITY_TYPES taxonomy)
        known_types = {t.lower() for t in ENTITY_TYPES}
        type_rows = (await db.execute(
            select(
                ExtractedEntity.entity_type,
                func.count(ExtractedEntity.id).label("cnt"),
            )
            .group_by(ExtractedEntity.entity_type)
        )).all()
        for row in type_rows:
            if row.entity_type and row.entity_type.lower() not in known_types:
                issues.append(KnowledgeIssue(
                    id=str(uuid.uuid4()),
                    issue_type="unknown_entity_type",
                    severity="warning",
                    description=(
                        f"Entity type '{row.entity_type}' is not in the known taxonomy "
                        f"({row.cnt} entities)"
                    ),
                    detail_json=json.dumps({
                        "entity_type": row.entity_type,
                        "count": row.cnt,
                    }),
                    detected_at=now,
                ))

        # 6 — sparse_relationships (> 5 entities but < 2 relationships per document)
        doc_entity_counts = (await db.execute(
            select(ExtractedEntity.document_id, func.count(ExtractedEntity.id).label("ecnt"))
            .group_by(ExtractedEntity.document_id)
            .having(func.count(ExtractedEntity.id) > 5)
        )).all()
        rel_count_rows = (await db.execute(
            select(ExtractedRelationship.document_id, func.count(ExtractedRelationship.id).label("rcnt"))
            .group_by(ExtractedRelationship.document_id)
        )).all()
        rel_count_map = {r.document_id: r.rcnt for r in rel_count_rows}
        for row in doc_entity_counts:
            rcnt = rel_count_map.get(row.document_id, 0)
            if rcnt < 2:
                issues.append(KnowledgeIssue(
                    id=str(uuid.uuid4()),
                    issue_type="sparse_relationships",
                    severity="info",
                    document_id=row.document_id,
                    description=(
                        f"Document has {row.ecnt} entities but only {rcnt} relationships — "
                        "consider re-running relationship extraction"
                    ),
                    detail_json=json.dumps({
                        "document_id": row.document_id,
                        "entity_count": row.ecnt,
                        "relationship_count": rcnt,
                    }),
                    detected_at=now,
                ))

        if issues:
            db.add_all(issues)
            await db.commit()
            logger.info("Knowledge issues detected: %d", len(issues))

        return issues

    # ── Ontology Proposals ────────────────────────────────────────────────────

    async def generate_proposals(self, db: AsyncSession) -> list[OntologyProposal]:
        """
        Use Claude Haiku to propose ontology changes based on unknown entity types
        and relationship types found in the graph.
        """
        # Clear existing pending proposals for a fresh run
        await db.execute(
            delete(OntologyProposal).where(OntologyProposal.status == "pending")
        )
        await db.flush()

        # Collect unknown entity types
        known_types = {t.lower() for t in ENTITY_TYPES}
        type_rows = (await db.execute(
            select(ExtractedEntity.entity_type, func.count(ExtractedEntity.id).label("cnt"))
            .group_by(ExtractedEntity.entity_type)
        )).all()
        unknown_entity_types = [
            (row.entity_type, row.cnt)
            for row in type_rows
            if row.entity_type and row.entity_type.lower() not in known_types
        ]

        # Collect unknown relationship types
        known_rel_types = {t.lower() for t in RELATIONSHIP_TYPES}
        rel_rows = (await db.execute(
            select(ExtractedRelationship.relationship_type, func.count(ExtractedRelationship.id).label("cnt"))
            .group_by(ExtractedRelationship.relationship_type)
        )).all()
        unknown_rel_types = [
            (row.relationship_type, row.cnt)
            for row in rel_rows
            if row.relationship_type and row.relationship_type.lower() not in known_rel_types
        ]

        # Also check OntologyVersion discovered classes vs manager classes
        ontology_class_names = {c.name.lower() for c in ontology_manager.list_classes()}
        version_rows = (await db.execute(
            select(OntologyVersion).order_by(OntologyVersion.created_at.desc()).limit(5)
        )).scalars().all()
        discovered_classes: list[dict] = []
        for version in version_rows:
            try:
                content = json.loads(version.ontology_json)
                for cls in content.get("classes", []):
                    if cls.get("name") and cls["name"].lower() not in ontology_class_names:
                        discovered_classes.append({
                            "name": cls["name"],
                            "description": cls.get("description", ""),
                        })
            except Exception:
                pass

        proposals: list[OntologyProposal] = []

        # Call Claude Haiku to classify unknown entity types
        if unknown_entity_types or unknown_rel_types:
            known_list = sorted(ENTITY_TYPES)
            unknown_ent_list = [f"{t} ({c} entities)" for t, c in unknown_entity_types]
            unknown_rel_list = [f"{t} ({c} rels)" for t, c in unknown_rel_types]

            system = (
                "You are an ontology engineer. Analyze unknown entity and relationship types "
                "found in a knowledge graph and propose ontology changes. "
                "Return ONLY a valid JSON array, no markdown fences, no explanation."
            )
            prompt = (
                f"Known entity types: {known_list}\n"
                f"Unknown entity types found in data: {unknown_ent_list}\n"
                f"Known relationship types: {sorted(RELATIONSHIP_TYPES)}\n"
                f"Unknown relationship types: {unknown_rel_list}\n\n"
                "For each unknown entity type, propose one action:\n"
                "  - add_class: add it as a new ontology class\n"
                "  - merge_class: merge it into an existing class (specify which)\n"
                "  - rename_class: rename it to follow naming conventions (specify new name)\n"
                "For each unknown relationship type, propose add_relationship.\n\n"
                "Return a JSON array:\n"
                '[{"proposal_type": "add_class|merge_class|rename_class|add_relationship", '
                '"subject": "the unknown type", "target": "merge/rename target or null", '
                '"description": "short description", "rationale": "why this change"}]'
            )

            try:
                raw = await anthropic_client.complete(
                    prompt,
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                    system=system,
                )
                cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                proposal_data = json.loads(cleaned)

                now = datetime.now(timezone.utc)
                for item in proposal_data:
                    if not isinstance(item, dict) or "proposal_type" not in item:
                        continue
                    proposals.append(OntologyProposal(
                        id=str(uuid.uuid4()),
                        proposal_type=item.get("proposal_type", "add_class"),
                        status="pending",
                        description=item.get("description", ""),
                        rationale=item.get("rationale", ""),
                        detail_json=json.dumps({
                            "subject": item.get("subject", ""),
                            "target": item.get("target"),
                        }),
                        proposed_at=now,
                    ))
            except Exception as exc:
                logger.warning("Proposal generation failed: %s", exc)

        # Add proposals from discovered OntologyVersion classes
        now = datetime.now(timezone.utc)
        for cls in discovered_classes:
            proposals.append(OntologyProposal(
                id=str(uuid.uuid4()),
                proposal_type="add_class",
                status="pending",
                description=f"Add ontology class '{cls['name']}' discovered in extracted ontology",
                rationale=(
                    f"Class '{cls['name']}' was discovered during ontology analysis "
                    "but is not in the active ontology manager."
                ),
                detail_json=json.dumps({
                    "subject": cls["name"],
                    "description": cls.get("description", ""),
                }),
                proposed_at=now,
            ))

        if proposals:
            db.add_all(proposals)
            await db.commit()
            logger.info("Ontology proposals generated: %d", len(proposals))

        return proposals

    # ── Auto-Correction ───────────────────────────────────────────────────────

    async def auto_correct(self, db: AsyncSession) -> int:
        """
        Apply safe auto-corrections:
          1. Delete exact duplicate entities (same name+document_id), keep highest confidence
          2. Normalize entity_type casing to match canonical ENTITY_TYPES values
        Returns: number of corrections applied.
        """
        corrections = 0

        # 1 — Exact duplicate removal
        dup_groups = (await db.execute(
            select(ExtractedEntity.name, ExtractedEntity.document_id)
            .group_by(ExtractedEntity.name, ExtractedEntity.document_id)
            .having(func.count(ExtractedEntity.id) > 1)
        )).all()

        for name, doc_id in dup_groups:
            rows = (await db.execute(
                select(ExtractedEntity)
                .where(
                    ExtractedEntity.name == name,
                    ExtractedEntity.document_id == doc_id,
                )
                .order_by(ExtractedEntity.confidence.desc())
            )).scalars().all()
            for duplicate in rows[1:]:  # keep the first (highest confidence)
                await db.delete(duplicate)
                corrections += 1

        # 2 — Entity type case normalization
        canonical = {t.lower(): t for t in ENTITY_TYPES}
        all_entities = (await db.execute(select(ExtractedEntity))).scalars().all()
        for e in all_entities:
            if not e.entity_type:
                continue
            norm = canonical.get(e.entity_type.lower())
            if norm and norm != e.entity_type:
                e.entity_type = norm
                corrections += 1

        if corrections:
            await db.commit()
            logger.info("Auto-corrections applied: %d", corrections)

        return corrections

    # ── Apply / Dismiss Proposals ─────────────────────────────────────────────

    async def apply_proposal(self, proposal_id: str, db: AsyncSession) -> tuple[bool, str]:
        """Apply a pending ontology proposal. Returns (success, message)."""
        proposal = await db.get(OntologyProposal, proposal_id)
        if not proposal:
            return False, "Proposal not found"
        if proposal.status != "pending":
            return False, f"Proposal is already {proposal.status}"

        detail = {}
        try:
            detail = json.loads(proposal.detail_json)
        except Exception:
            pass

        message = ""
        if proposal.proposal_type == "add_class":
            class_name = detail.get("subject") or detail.get("class_name", "")
            class_desc = detail.get("description", proposal.description)
            if class_name:
                try:
                    ontology_manager.create_class(class_name, description=class_desc)
                    message = f"Added ontology class '{class_name}'"
                except ValueError:
                    message = f"Class '{class_name}' already exists — marked as applied"
            else:
                message = "No class name in proposal detail"
        elif proposal.proposal_type == "add_relationship":
            rel_type = detail.get("subject", "")
            if rel_type:
                _EXTENDED_RELATIONSHIP_TYPES[rel_type.lower()] = rel_type
                message = f"Registered relationship type '{rel_type}' (active until restart)"
            else:
                message = "No relationship type in proposal detail"
        else:
            # merge_class / rename_class — informational; user applies manually
            message = (
                f"Proposal marked applied — manual graph rebuild required "
                f"to propagate {proposal.proposal_type}"
            )

        proposal.status = "applied"
        proposal.applied_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("Applied proposal %s: %s", proposal_id, message)
        return True, message

    async def dismiss_proposal(self, proposal_id: str, db: AsyncSession) -> bool:
        """Dismiss a pending proposal."""
        proposal = await db.get(OntologyProposal, proposal_id)
        if not proposal:
            return False
        proposal.status = "dismissed"
        await db.commit()
        return True

    # ── Full Analysis Pipeline ────────────────────────────────────────────────

    async def analyze(
        self,
        db: AsyncSession,
        auto_correct: bool = False,
        threshold: float = 0.5,
    ) -> AnalysisResult:
        t0 = time.monotonic()

        issues = await self.detect_issues(db, threshold)
        proposals = await self.generate_proposals(db)
        corrections = await self.auto_correct(db) if auto_correct else 0
        metrics = await self.compute_metrics(db, threshold)

        return AnalysisResult(
            metrics=metrics,
            issues_detected=len(issues),
            proposals_generated=len(proposals),
            auto_corrections_applied=corrections,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )


# Module-level singleton
knowledge_evolution_engine = KnowledgeEvolutionEngine()
