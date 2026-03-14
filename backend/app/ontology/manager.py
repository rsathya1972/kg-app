"""
Ontology manager: in-memory CRUD for ontology classes and properties.
Will be backed by PostgreSQL in a later step.
"""
from app.ontology.base import OntologyClass, OntologyProperty
from app.logger import get_logger
import uuid

logger = get_logger(__name__)


class OntologyManager:
    """
    Manages the domain ontology: classes, properties, and their relationships.
    Currently uses in-memory dicts. PostgreSQL persistence added in Step 4.
    """

    def __init__(self) -> None:
        self._classes: dict[str, OntologyClass] = {}
        self._properties: dict[str, OntologyProperty] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        """Seed a minimal default ontology for bootstrapping."""
        defaults = [
            OntologyClass(name="Entity", description="Root class for all entities"),
            OntologyClass(name="Person", parent_class="Entity", description="A human individual",
                          properties=["name", "birth_date", "nationality"]),
            OntologyClass(name="Organization", parent_class="Entity", description="A company, institution, or group",
                          properties=["name", "founded_date", "headquarters"]),
            OntologyClass(name="Location", parent_class="Entity", description="A geographic place",
                          properties=["name", "country", "coordinates"]),
            OntologyClass(name="Concept", parent_class="Entity", description="An abstract idea or domain concept",
                          properties=["name", "definition"]),
        ]
        for cls in defaults:
            self._classes[cls.id] = cls
        logger.debug("Seeded %d default ontology classes", len(defaults))

    # ── Classes ──────────────────────────────────────────────────────────────

    def list_classes(self) -> list[OntologyClass]:
        return list(self._classes.values())

    def get_class(self, class_id: str) -> OntologyClass | None:
        return self._classes.get(class_id)

    def get_class_by_name(self, name: str) -> OntologyClass | None:
        return next((c for c in self._classes.values() if c.name.lower() == name.lower()), None)

    def create_class(self, name: str, description: str | None = None,
                     parent_class: str | None = None) -> OntologyClass:
        if self.get_class_by_name(name):
            raise ValueError(f"Ontology class '{name}' already exists")
        cls = OntologyClass(id=str(uuid.uuid4()), name=name,
                            description=description, parent_class=parent_class)
        self._classes[cls.id] = cls
        logger.info("Created ontology class: %s", name)
        return cls

    def delete_class(self, class_id: str) -> bool:
        if class_id in self._classes:
            del self._classes[class_id]
            return True
        return False

    # ── Properties ───────────────────────────────────────────────────────────

    def list_properties(self, domain_class: str | None = None) -> list[OntologyProperty]:
        props = list(self._properties.values())
        if domain_class:
            props = [p for p in props if p.domain_class == domain_class]
        return props

    def create_property(self, name: str, domain_class: str,
                        range_type: str = "string", required: bool = False) -> OntologyProperty:
        prop = OntologyProperty(id=str(uuid.uuid4()), name=name,
                                domain_class=domain_class, range_type=range_type,
                                required=required)
        self._properties[prop.id] = prop
        logger.info("Created ontology property: %s.%s", domain_class, name)
        return prop


# Module-level singleton
ontology_manager = OntologyManager()
