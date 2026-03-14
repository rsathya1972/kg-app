"""
Mock relationship extractor for tests and development without an API key.
Returns deterministic fake relationships using entity names present in the document.
"""
from app.extraction.base import Entity, ExtractionResult, Relation
from app.logger import get_logger

logger = get_logger(__name__)

# Deterministic template relations; source/target filled from available entity names
_MOCK_TEMPLATES = [
    ("WORKS_FOR", 0, 1, 0.92, "Mock: person works for company"),
    ("USES",      1, 2, 0.88, "Mock: company uses technology"),
    ("LOCATED_IN",0, 3, 0.85, "Mock: entity is located in location"),
    ("GOVERNED_BY",1, 4, 0.80, "Mock: entity governed by regulation"),
    ("DEPENDS_ON", 2, 1, 0.75, "Mock: technology depends on product"),
]


class MockRelationExtractor:
    """
    Returns deterministic fake relationships without calling any AI API.
    Useful in tests and local development when ANTHROPIC_API_KEY is unavailable.
    """

    async def extract_from_entities(
        self,
        document_id: str,
        text: str,
        entities: list[Entity],
    ) -> ExtractionResult:
        logger.info(
            "MockRelationExtractor: generating fake relations for document_id=%s "
            "with %d entities",
            document_id, len(entities),
        )

        if len(entities) < 2:
            return ExtractionResult(document_id=document_id, model_used="mock")

        relations: list[Relation] = []
        for predicate, src_idx, tgt_idx, confidence, evidence in _MOCK_TEMPLATES:
            if src_idx >= len(entities) or tgt_idx >= len(entities):
                continue
            source = entities[src_idx]
            target = entities[tgt_idx]
            if source.id == target.id:
                continue
            relations.append(Relation(
                subject_id=source.id,
                predicate=predicate,
                object_id=target.id,
                confidence=confidence,
                evidence=evidence,
            ))

        logger.info(
            "MockRelationExtractor: produced %d relations for document_id=%s",
            len(relations), document_id,
        )
        return ExtractionResult(
            document_id=document_id,
            relations=relations,
            model_used="mock",
        )
