"""
Ontology aligner: maps extracted entities to ontology classes using AI.
Stub — AI calls wired in a later step.
"""
from app.extraction.base import Entity
from app.logger import get_logger
from app.ontology.manager import ontology_manager

logger = get_logger(__name__)

ALIGNMENT_PROMPT = """
Map each entity to the most appropriate ontology class.
Available classes: {class_list}

Return ONLY valid JSON:
{
  "alignments": [
    {"entity_text": "...", "ontology_class": "...", "confidence": 0.0-1.0}
  ]
}
NEVER assign a class not in the available list.

Entities:
{entities_json}
"""


class OntologyAligner:
    """Maps extracted entities to ontology classes using an AI model."""

    def __init__(self, provider: str = "anthropic") -> None:
        self.provider = provider

    async def align(self, entities: list[Entity]) -> list[dict]:
        """
        Align entities to ontology classes.

        Args:
            entities: List of extracted Entity objects.

        Returns:
            List of {entity_id, ontology_class, confidence} dicts.

        Raises:
            NotImplementedError: Until AI client is wired.
        """
        classes = [c.name for c in ontology_manager.list_classes()]
        logger.info(
            "Aligning %d entities against %d ontology classes",
            len(entities), len(classes),
        )
        raise NotImplementedError(
            "OntologyAligner.align() is a stub. Wire up AI client in a later step."
        )
