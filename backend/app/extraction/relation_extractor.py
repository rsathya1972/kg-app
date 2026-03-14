"""
AI-powered relationship extraction between named entities using Claude.

Extracts directed relationships of types:
  WORKS_FOR, OWNS, USES, BELONGS_TO, RENEWS, EXPIRES_ON,
  LOCATED_IN, DEPENDS_ON, SELLS_TO, GOVERNED_BY
"""
import json
import re

from app.ai.anthropic_client import anthropic_client
from app.extraction.base import (
    RELATIONSHIP_TYPES,
    BaseExtractor,
    Entity,
    ExtractionResult,
    Relation,
)
from app.logger import get_logger
from app.preprocessing.chunker import SlidingWindowChunker

logger = get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"

RELATION_EXTRACTION_PROMPT = """\
You are an expert at identifying relationships between named entities in documents.
Given the text and a list of known entities, find all relationships between them.
Return ONLY valid JSON — no markdown fences, no commentary.

Schema:
{{
  "relations": [
    {{
      "source": "exact entity name from the Entities list",
      "type": "WORKS_FOR|OWNS|USES|BELONGS_TO|RENEWS|EXPIRES_ON|LOCATED_IN|DEPENDS_ON|SELLS_TO|GOVERNED_BY",
      "target": "exact entity name from the Entities list",
      "evidence": "verbatim excerpt ≤200 chars from the text supporting this relationship",
      "confidence": 0.0
    }}
  ]
}}

Rules:
- NEVER fabricate relationships not supported by the text.
- source and target MUST exactly match a name from the Entities list below.
- Use only one of the 10 listed relationship types.
- evidence must be a verbatim excerpt from the chunk text (max 200 chars).
- If no relationships are found, return {{"relations": []}}.

Entities:
{entities_json}

Text:
{text}
"""


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _deduplicate(relations: list[Relation]) -> list[Relation]:
    """Keep highest-confidence relation for each (subject_id, predicate, object_id) triple."""
    best: dict[tuple[str, str, str], Relation] = {}
    for rel in relations:
        key = (rel.subject_id.lower(), rel.predicate, rel.object_id.lower())
        existing = best.get(key)
        if existing is None or (rel.confidence or 0) > (existing.confidence or 0):
            best[key] = rel
    return list(best.values())


class RelationExtractor(BaseExtractor):
    """Extracts entity relationships from document text using Claude (Haiku)."""

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        self._chunker = SlidingWindowChunker(max_tokens=chunk_size, overlap_tokens=overlap)

    async def extract(self, document_id: str, text: str) -> ExtractionResult:
        """Generic extraction without pre-known entities — no-op, use extract_from_entities."""
        return await self.extract_from_entities(document_id, text, [])

    async def extract_from_entities(
        self,
        document_id: str,
        text: str,
        entities: list[Entity],
    ) -> ExtractionResult:
        """Extract relationships between known entities in the document text."""
        logger.info(
            "Starting relation extraction for document_id=%s with %d entities",
            document_id, len(entities),
        )

        name_to_entity: dict[str, Entity] = {e.text.lower(): e for e in entities}

        if not name_to_entity:
            logger.warning("No entities provided for document_id=%s — skipping", document_id)
            return ExtractionResult(document_id=document_id, model_used=MODEL)

        chunks = self._chunker.chunk(text)
        all_relations: list[Relation] = []

        for chunk in chunks:
            chunk_lower = chunk.text.lower()

            visible_names = [name for name in name_to_entity if name in chunk_lower]
            if len(visible_names) < 2:
                continue

            visible_entities = [name_to_entity[n] for n in visible_names]
            entities_json = json.dumps(
                [{"name": e.text, "type": e.label} for e in visible_entities],
                indent=2,
            )

            prompt = RELATION_EXTRACTION_PROMPT.format(
                entities_json=entities_json,
                text=chunk.text,
            )

            try:
                raw = await anthropic_client.complete(prompt, model=MODEL, max_tokens=2048)
            except Exception as exc:
                logger.error(
                    "Claude API error on chunk %d of doc %s: %s",
                    chunk.index, document_id, exc,
                )
                raise

            try:
                parsed = json.loads(_strip_fences(raw))
                raw_relations = parsed.get("relations", [])
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning(
                    "Failed to parse relation response for chunk %d of doc %s: %s",
                    chunk.index, document_id, exc,
                )
                continue

            for item in raw_relations:
                rel_type = str(item.get("type", "")).strip().upper()
                if rel_type not in RELATIONSHIP_TYPES:
                    logger.debug("Skipping unknown relationship type %r", rel_type)
                    continue

                source_name = str(item.get("source", "")).strip()
                target_name = str(item.get("target", "")).strip()

                source_entity = name_to_entity.get(source_name.lower())
                target_entity = name_to_entity.get(target_name.lower())

                if source_entity is None or target_entity is None:
                    logger.debug(
                        "Skipping relation — unknown entity: source=%r target=%r",
                        source_name, target_name,
                    )
                    continue

                evidence = str(item.get("evidence", "")).strip()[:500]

                confidence_raw = item.get("confidence", 0.8)
                try:
                    confidence = float(confidence_raw)
                except (TypeError, ValueError):
                    confidence = 0.8
                confidence = max(0.0, min(1.0, confidence))

                all_relations.append(Relation(
                    subject_id=source_entity.id,
                    predicate=rel_type,
                    object_id=target_entity.id,
                    confidence=confidence,
                    evidence=evidence,
                ))

        deduped = _deduplicate(all_relations)

        logger.info(
            "Relation extraction complete for document_id=%s: %d relations "
            "(%d before dedup) across %d chunks",
            document_id, len(deduped), len(all_relations), len(chunks),
        )
        return ExtractionResult(
            document_id=document_id,
            relations=deduped,
            model_used=MODEL,
        )
