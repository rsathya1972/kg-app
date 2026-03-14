from datetime import datetime

from pydantic import BaseModel


class OntologyClassRequest(BaseModel):
    name: str
    description: str | None = None
    parent_class: str | None = None
    properties: list[str] | None = None


class OntologyClassResponse(BaseModel):
    id: str
    name: str
    description: str | None
    parent_class: str | None
    properties: list[str]


class OntologyPropertyRequest(BaseModel):
    name: str
    domain_class: str
    range_type: str     # e.g. "string", "integer", "OntologyClass name"
    required: bool = False


class OntologyPropertyResponse(BaseModel):
    id: str
    name: str
    domain_class: str
    range_type: str
    required: bool


class AlignmentRequest(BaseModel):
    document_id: str
    entity_ids: list[str] | None = None   # None = align all entities


class AlignmentResultResponse(BaseModel):
    document_id: str
    aligned_count: int
    unresolved_count: int
    alignments: list[dict]   # [{entity_id, ontology_class, confidence}]


# ── Ontology Discovery (versioned) ────────────────────────────────────────────

class OntologyAttribute(BaseModel):
    name: str
    type: str                  # "string" | "integer" | "float" | "boolean" | "date" | "reference"
    description: str | None = None


class OntologyClassDiscovered(BaseModel):
    name: str
    description: str | None = None
    attributes: list[OntologyAttribute] = []
    synonyms: list[str] = []
    parent_class: str | None = None


class OntologyRelationshipDiscovered(BaseModel):
    source_class: str
    predicate: str
    target_class: str
    description: str | None = None


class OntologyContent(BaseModel):
    domain: str
    classes: list[OntologyClassDiscovered]
    relationships: list[OntologyRelationshipDiscovered]


class OntologyGenerateRequest(BaseModel):
    document_id: str | None = None
    domain_hint: str | None = None


class OntologyVersionSummary(BaseModel):
    id: str
    version: int
    document_id: str | None
    domain_hint: str | None
    classes_count: int
    relationships_count: int
    model_used: str
    created_at: datetime


class OntologyVersionDetail(OntologyVersionSummary):
    ontology: OntologyContent


class OntologyListResponse(BaseModel):
    versions: list[OntologyVersionSummary]
    total: int
