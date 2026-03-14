"""
Core ontology dataclasses: OntologyClass and OntologyProperty.
"""
from dataclasses import dataclass, field
import uuid


@dataclass
class OntologyProperty:
    """A property (attribute or relation) that an OntologyClass may have."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain_class: str = ""        # Class this property belongs to
    range_type: str = "string"   # "string" | "integer" | "float" | "boolean" | <ClassName>
    required: bool = False
    description: str | None = None


@dataclass
class OntologyClass:
    """
    A class in the domain ontology (analogous to an OWL class).

    Example:
        OntologyClass(name="Person", properties=["name", "birth_date", "nationality"])
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str | None = None
    parent_class: str | None = None     # Single inheritance for simplicity
    properties: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)

    def is_subclass_of(self, class_name: str) -> bool:
        """Naive single-level subclass check."""
        return self.parent_class == class_name
