"""
Consistency checker: validates logical rules that can be checked without SHACL.
These run against in-memory data and don't require Neo4j.
"""
from app.extraction.base import Entity, Relation
from app.logger import get_logger
from app.ontology.manager import ontology_manager
from app.validation.base import Severity, ValidationReport, ValidationViolation

logger = get_logger(__name__)


class ConsistencyChecker:
    """Checks logical consistency rules over entities and relations."""

    def check(
        self,
        entities: list[Entity],
        relations: list[Relation],
        document_id: str | None = None,
    ) -> ValidationReport:
        """
        Run consistency checks on extracted entities and relations.

        Checks:
        - Every entity has a non-empty text value
        - Every relation references valid entity IDs
        - Relation predicates are non-empty

        Args:
            entities: Extracted entities.
            relations: Extracted relations.
            document_id: Optional document scope for the report.

        Returns:
            ValidationReport
        """
        violations: list[ValidationViolation] = []
        entity_ids = {e.id for e in entities}

        for entity in entities:
            if not entity.text.strip():
                violations.append(ValidationViolation(
                    rule_id="ENT_001",
                    severity=Severity.ERROR,
                    message="Entity has empty text",
                    node_id=entity.id,
                ))

        for relation in relations:
            if relation.subject_id not in entity_ids:
                violations.append(ValidationViolation(
                    rule_id="REL_001",
                    severity=Severity.ERROR,
                    message=f"Relation subject '{relation.subject_id}' not found in entities",
                    node_id=relation.id,
                ))
            if relation.object_id not in entity_ids:
                violations.append(ValidationViolation(
                    rule_id="REL_002",
                    severity=Severity.ERROR,
                    message=f"Relation object '{relation.object_id}' not found in entities",
                    node_id=relation.id,
                ))
            if not relation.predicate.strip():
                violations.append(ValidationViolation(
                    rule_id="REL_003",
                    severity=Severity.WARNING,
                    message="Relation has empty predicate",
                    node_id=relation.id,
                ))

        total = len(entities) + len(relations)
        logger.info(
            "Consistency check: %d items checked, %d violations",
            total, len(violations),
        )

        return ValidationReport(
            document_id=document_id,
            rule_set="consistency",
            total_checked=total,
            violations=violations,
        )
