"""
OntologyDiscoveryAgent: uses Claude Sonnet to infer a domain ontology from
extracted entities and relationships.

Input:  lists of ExtractedEntity + ExtractedRelationship rows from the DB
Output: parsed dict matching the OntologyContent JSON schema

The agent groups entities by type and deduplicates relationship triples into
class-level patterns before sending to Claude, keeping the prompt compact.
"""
import json
import re
from collections import Counter, defaultdict

from app.ai.anthropic_client import anthropic_client
from app.db.models import ExtractedEntity, ExtractedRelationship
from app.logger import get_logger

logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 4096

_SYSTEM_PROMPT = """\
You are an expert ontology engineer. Given a set of extracted named entities and \
relationship patterns from documents, infer a clean domain ontology.

Return ONLY valid JSON — no markdown fences, no commentary, no explanation.

Output schema:
{
  "domain": "short domain name inferred from the data",
  "classes": [
    {
      "name": "ClassName",
      "description": "one-sentence description of this class",
      "attributes": [
        {"name": "attr_name", "type": "string|integer|float|boolean|date|reference", "description": "what this attribute means"}
      ],
      "synonyms": ["AlternativeName"],
      "parent_class": null
    }
  ],
  "relationships": [
    {
      "source_class": "ClassName",
      "predicate": "RELATIONSHIP_TYPE",
      "target_class": "ClassName",
      "description": "what this relationship means"
    }
  ]
}

Rules:
- ONLY create classes that correspond to observed entity types — NEVER fabricate.
- Attributes should reflect real properties of the entity type (e.g. a Contract has contract_id, value, renewal_date).
- parent_class must be null or the name of another class in the classes list.
- Deduplicate relationships — one entry per (source_class, predicate, target_class) triple.
- Return at least 2 attributes per class where domain knowledge supports it.\
"""


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences."""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL)


def _build_prompt(
    entities: list[ExtractedEntity],
    relationships: list[ExtractedRelationship],
    domain_hint: str | None,
) -> str:
    # Group entity names by type
    by_type: dict[str, list[str]] = defaultdict(list)
    for e in entities:
        by_type[e.entity_type].append(e.name)

    entity_lines = []
    for etype, names in sorted(by_type.items()):
        unique_names = list(dict.fromkeys(names))  # preserve order, deduplicate
        sample = unique_names[:10]
        suffix = f" (+{len(unique_names) - 10} more)" if len(unique_names) > 10 else ""
        entity_lines.append(
            f"  {etype} ({len(names)} instances): {', '.join(sample)}{suffix}"
        )

    # Deduplicate relationship triples to class-level patterns
    pattern_counts: Counter[tuple[str, str, str]] = Counter()
    # Build entity id → type lookup
    entity_id_to_type: dict[str, str] = {e.id: e.entity_type for e in entities}
    entity_name_to_type: dict[str, str] = {e.name: e.entity_type for e in entities}

    for r in relationships:
        src_type = (
            entity_id_to_type.get(r.source_entity_id or "")
            or entity_name_to_type.get(r.source_entity_name, "Unknown")
        )
        tgt_type = (
            entity_id_to_type.get(r.target_entity_id or "")
            or entity_name_to_type.get(r.target_entity_name, "Unknown")
        )
        pattern_counts[(src_type, r.relationship_type, tgt_type)] += 1

    rel_lines = []
    for (src, pred, tgt), count in sorted(
        pattern_counts.items(), key=lambda x: -x[1]
    ):
        rel_lines.append(f"  {src} --{pred}--> {tgt}  ({count} occurrence{'s' if count != 1 else ''})")

    domain_str = domain_hint or "infer from data"

    parts = [
        f"Domain hint: {domain_str}",
        "",
        "Entity types observed:",
        *entity_lines,
        "",
        "Relationship patterns observed:",
        *(rel_lines or ["  (none)"]),
    ]
    return "\n".join(parts)


class OntologyDiscoveryAgent:
    """
    Calls Claude Sonnet to discover a domain ontology from extracted artifacts.
    Returns the parsed ontology dict (caller handles persistence).
    """

    async def discover(
        self,
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship],
        domain_hint: str | None = None,
    ) -> dict:
        logger.info(
            "OntologyDiscoveryAgent: %d entities, %d relationships, hint=%r",
            len(entities),
            len(relationships),
            domain_hint,
        )

        prompt = _build_prompt(entities, relationships, domain_hint)
        raw = await anthropic_client.complete(
            prompt,
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
        )

        cleaned = _strip_fences(raw)
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("OntologyDiscoveryAgent: JSON parse failed: %s\nRaw: %s", exc, cleaned[:500])
            raise ValueError(f"Claude returned invalid JSON: {exc}") from exc

        logger.info(
            "OntologyDiscoveryAgent: discovered %d classes, %d relationships, domain=%r",
            len(result.get("classes", [])),
            len(result.get("relationships", [])),
            result.get("domain"),
        )
        return result


ontology_discovery_agent = OntologyDiscoveryAgent()
