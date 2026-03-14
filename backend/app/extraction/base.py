"""
Base interfaces and dataclasses for entity and relation extraction.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import uuid

# Supported entity types for the knowledge graph domain
ENTITY_TYPES: frozenset[str] = frozenset({
    "Company",
    "Person",
    "Product",
    "Contract",
    "Location",
    "Technology",
    "Policy",
    "Regulation",
})

# Supported directed relationship types
RELATIONSHIP_TYPES: frozenset[str] = frozenset({
    "WORKS_FOR",
    "OWNS",
    "USES",
    "BELONGS_TO",
    "RENEWS",
    "EXPIRES_ON",
    "LOCATED_IN",
    "DEPENDS_ON",
    "SELLS_TO",
    "GOVERNED_BY",
})


@dataclass
class Entity:
    """A named entity extracted from text."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    label: str = ""            # e.g. "PERSON", "ORG", "CONCEPT", "LOCATION"
    start_char: int | None = None
    end_char: int | None = None
    confidence: float | None = None
    source_chunk: int | None = None
    attributes: dict = field(default_factory=dict)


@dataclass
class Relation:
    """A directed relationship between two entities."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject_id: str = ""
    predicate: str = ""        # e.g. "WORKS_FOR", "LOCATED_IN", "CAUSES"
    object_id: str = ""
    confidence: float | None = None
    evidence: str | None = None   # source sentence


@dataclass
class ExtractionResult:
    """The full output of running an extractor on a document."""
    document_id: str
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    model_used: str | None = None


class BaseExtractor(ABC):
    """Abstract base class for entity/relation extractors."""

    @abstractmethod
    async def extract(self, document_id: str, text: str) -> ExtractionResult:
        """
        Extract entities and/or relations from text.

        Args:
            document_id: ID of the source document.
            text: Cleaned text (or a single chunk) to extract from.

        Returns:
            ExtractionResult
        """
