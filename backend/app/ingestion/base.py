"""
Base interface for all document ingesters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class IngestedDocument:
    """Represents a document after initial ingestion (before preprocessing)."""
    id: str
    source_type: str               # "file" | "url" | "text"
    raw_text: str
    filename: str | None = None
    mime_type: str | None = None
    source_url: str | None = None
    size_kb: float | None = None
    language: str | None = None
    metadata: dict = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.utcnow)


class BaseIngester(ABC):
    """Abstract base class for all ingester implementations."""

    @abstractmethod
    async def can_handle(self, source: str) -> bool:
        """Return True if this ingester can handle the given source."""

    @abstractmethod
    async def ingest(self, source: str, metadata: dict | None = None) -> IngestedDocument:
        """
        Ingest a document from the given source.

        Args:
            source: File path, URL, or raw text depending on ingester type.
            metadata: Optional caller-provided metadata merged into document.

        Returns:
            IngestedDocument with raw_text populated.
        """
