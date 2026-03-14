"""
Pydantic schemas for the Knowledge Evolution Engine.
"""
import json
from datetime import datetime

from pydantic import BaseModel, field_validator


class KnowledgeIssueResponse(BaseModel):
    id: str
    issue_type: str
    severity: str
    entity_id: str | None
    relationship_id: str | None
    document_id: str | None
    description: str
    detail: dict
    status: str
    detected_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("detail", mode="before")
    @classmethod
    def parse_detail(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v or {}


class OntologyProposalResponse(BaseModel):
    id: str
    proposal_type: str
    status: str
    description: str
    rationale: str
    detail: dict
    proposed_at: datetime
    applied_at: datetime | None

    model_config = {"from_attributes": True}

    @field_validator("detail", mode="before")
    @classmethod
    def parse_detail(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v or {}


class EvaluationMetrics(BaseModel):
    entity_count: int
    relationship_count: int
    entity_accuracy: float          # 0.0–1.0 (% with confidence >= threshold)
    relationship_accuracy: float    # 0.0–1.0
    ontology_coverage: float        # 0.0–1.0 (% entity types in ontology)
    graph_completeness: float       # avg relationships per entity
    low_confidence_entities: int
    low_confidence_relationships: int
    duplicate_entities: int         # entity groups with count > 1
    orphan_entities: int            # entities with no relationships
    unique_entity_types: int
    ontology_class_count: int
    neo4j_node_count: int           # 0 if Neo4j unavailable
    neo4j_edge_count: int           # 0 if Neo4j unavailable


class AnalysisResult(BaseModel):
    metrics: EvaluationMetrics
    issues_detected: int
    proposals_generated: int
    auto_corrections_applied: int
    duration_ms: int


class TriggerAnalysisRequest(BaseModel):
    auto_correct: bool = False
    confidence_threshold: float = 0.5


class IssueListResponse(BaseModel):
    issues: list[KnowledgeIssueResponse]
    total: int


class ProposalListResponse(BaseModel):
    proposals: list[OntologyProposalResponse]
    total: int
