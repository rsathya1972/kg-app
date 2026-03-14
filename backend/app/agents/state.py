"""
Pipeline state TypedDict — threaded through every graph node.
Follows the LangGraph state pattern (compatible API).
"""
from typing import TypedDict


class PipelineState(TypedDict):
    run_id: str
    document_id: str
    document_text: str | None       # loaded by entity_extraction_node
    domain_hint: str | None

    # Step outputs (populated progressively)
    entity_ids: list[str]           # persisted ExtractedEntity IDs
    relationship_ids: list[str]     # persisted ExtractedRelationship IDs
    ontology_version_id: str | None
    graph_stats: dict | None
    embed_result: dict | None

    # Tracking
    errors: list[str]
    decisions: list[dict]           # {agent, message, timestamp}
    completed_steps: list[str]
