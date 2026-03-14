from datetime import datetime

from pydantic import BaseModel


class ExtractRequest(BaseModel):
    document_id: str
    extract_entities: bool = True
    extract_relations: bool = False
    extract_events: bool = False


class EntityResponse(BaseModel):
    id: str
    document_id: str
    entity_type: str
    name: str
    attributes: dict
    evidence_chunk: str
    confidence: float
    created_at: datetime


class EntityListResponse(BaseModel):
    entities: list[EntityResponse]
    total: int


class RelationshipResponse(BaseModel):
    id: str
    document_id: str
    source_entity_id: str | None
    target_entity_id: str | None
    source_entity_name: str
    target_entity_name: str
    relationship_type: str
    confidence: float
    evidence_text: str
    created_at: datetime


class RelationshipListResponse(BaseModel):
    relationships: list[RelationshipResponse]
    total: int


# Legacy — kept for backward compatibility with the /extract stub routes
class RelationResponse(BaseModel):
    id: str
    subject_id: str
    predicate: str
    object_id: str
    confidence: float | None = None


class ExtractionResultResponse(BaseModel):
    document_id: str
    entities: list[EntityResponse]
    relations: list[RelationResponse]
    event_count: int = 0
    model_used: str | None = None
