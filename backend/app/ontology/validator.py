"""
Ontology validator: checks that entities conform to ontology class constraints.
"""
from dataclasses import dataclass
from app.extraction.base import Entity
from app.logger import get_logger
from app.ontology.manager import ontology_manager

logger = get_logger(__name__)


@dataclass
class ConstraintViolation:
    entity_id: str
    entity_text: str
    ontology_class: str | None
    message: str
    severity: str = "warning"   # "error" | "warning"


class OntologyValidator:
    """Validates that extracted and aligned entities satisfy ontology constraints."""

    def validate(self, entities: list[Entity], alignments: list[dict]) -> list[ConstraintViolation]:
        """
        Check each entity's alignment against ontology class definitions.

        Args:
            entities: List of extracted entities.
            alignments: [{entity_id, ontology_class, confidence}]

        Returns:
            List of ConstraintViolations (empty = all valid).
        """
        violations: list[ConstraintViolation] = []
        alignment_map = {a["entity_id"]: a for a in alignments}

        for entity in entities:
            alignment = alignment_map.get(entity.id)

            if not alignment:
                violations.append(ConstraintViolation(
                    entity_id=entity.id,
                    entity_text=entity.text,
                    ontology_class=None,
                    message="Entity has no ontology alignment",
                    severity="warning",
                ))
                continue

            class_name = alignment.get("ontology_class")
            if class_name and not ontology_manager.get_class_by_name(class_name):
                violations.append(ConstraintViolation(
                    entity_id=entity.id,
                    entity_text=entity.text,
                    ontology_class=class_name,
                    message=f"Aligned class '{class_name}' does not exist in ontology",
                    severity="error",
                ))

        logger.info(
            "Validation: %d entities, %d violations",
            len(entities), len(violations),
        )
        return violations
