"""
AI-powered named entity recognition (NER) using Claude.
Extracts entities of types: Company, Person, Product, Contract,
Location, Technology, Policy, Regulation.
"""
import json
import re

from app.ai.anthropic_client import anthropic_client
from app.extraction.base import ENTITY_TYPES, BaseExtractor, Entity, ExtractionResult
from app.logger import get_logger
from app.preprocessing.chunker import SlidingWindowChunker

logger = get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"

ENTITY_EXTRACTION_PROMPT = """\
Extract all named entities from the text below.
Return ONLY valid JSON — no markdown fences, no commentary.

Schema:
{{
  "entities": [
    {{
      "name": "full entity name as it appears in the text",
      "type": "Company|Person|Product|Contract|Location|Technology|Policy|Regulation",
      "attributes": {{"key": "value"}},
      "evidence": "verbatim excerpt (≤ 200 chars) from the text that mentions this entity",
      "confidence": 0.0
    }}
  ]
}}

Rules:
- NEVER fabricate entities not present in the text.
- Only use one of the 8 types listed above; skip entities that don't fit.
- evidence must be a verbatim excerpt from the chunk text (max 200 characters).
- attributes should capture relevant details (role, value, date, version, jurisdiction, etc.).
- confidence is a float 0.0–1.0 reflecting how certain you are this is a real entity.

Text:
{text}
"""


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences if Claude wraps its JSON response."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


class EntityExtractionAgent(BaseExtractor):
    """Extracts named entities from document text using Claude (Haiku)."""

    def __init__(self, chunk_size: int = 600, overlap: int = 50) -> None:
        self._chunker = SlidingWindowChunker(max_tokens=chunk_size, overlap_tokens=overlap)

    async def extract(self, document_id: str, text: str) -> ExtractionResult:
        logger.info("Starting entity extraction for document_id=%s", document_id)

        chunks = self._chunker.chunk(text)
        if not chunks:
            logger.warning("No chunks produced for document_id=%s", document_id)
            return ExtractionResult(document_id=document_id, model_used=MODEL)

        all_entities: list[Entity] = []

        for chunk in chunks:
            prompt = ENTITY_EXTRACTION_PROMPT.format(text=chunk.text)
            try:
                raw = await anthropic_client.complete(
                    prompt,
                    model=MODEL,
                    max_tokens=2048,
                )
            except Exception as exc:
                # Re-raise auth/network errors immediately so the caller can surface them
                logger.error(
                    "Claude API error on chunk %d of doc %s: %s",
                    chunk.index, document_id, exc,
                )
                raise

            try:
                parsed = json.loads(_strip_fences(raw))
                raw_entities = parsed.get("entities", [])
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning(
                    "Failed to parse extraction response for chunk %d of doc %s: %s",
                    chunk.index, document_id, exc,
                )
                continue

            for item in raw_entities:
                entity_type = item.get("type", "").strip()
                if entity_type not in ENTITY_TYPES:
                    logger.debug("Skipping unknown entity type %r", entity_type)
                    continue

                name = str(item.get("name", "")).strip()
                if not name:
                    continue

                evidence = str(item.get("evidence", "")).strip()[:500]
                attributes = item.get("attributes", {})
                if not isinstance(attributes, dict):
                    attributes = {}

                confidence_raw = item.get("confidence", 0.8)
                try:
                    confidence = float(confidence_raw)
                except (TypeError, ValueError):
                    confidence = 0.8
                confidence = max(0.0, min(1.0, confidence))

                all_entities.append(Entity(
                    text=name,
                    label=entity_type,
                    source_chunk=chunk.index,
                    confidence=confidence,
                    attributes={**attributes, "_evidence": evidence},
                ))

        logger.info(
            "Extraction complete for document_id=%s: %d entities across %d chunks",
            document_id, len(all_entities), len(chunks),
        )
        return ExtractionResult(
            document_id=document_id,
            entities=all_entities,
            model_used=MODEL,
        )
