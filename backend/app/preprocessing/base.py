"""
Base interface for text preprocessors.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TextChunk:
    """A segment of text produced by a chunker."""
    index: int
    text: str
    start_char: int
    end_char: int
    token_count: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class PreprocessedDocument:
    """Document after cleaning and chunking."""
    document_id: str
    cleaned_text: str
    language: str | None
    chunks: list[TextChunk]
    word_count: int
    token_count: int | None = None


class BasePreprocessor(ABC):
    """Abstract base class for text preprocessors."""

    @abstractmethod
    def clean(self, text: str) -> str:
        """Clean raw text: normalize whitespace, fix encoding, etc."""

    @abstractmethod
    def chunk(self, text: str) -> list[TextChunk]:
        """Split cleaned text into chunks suitable for AI processing."""

    def process(self, document_id: str, raw_text: str, language: str | None = None) -> PreprocessedDocument:
        """Full pipeline: clean → chunk → return PreprocessedDocument."""
        cleaned = self.clean(raw_text)
        chunks = self.chunk(cleaned)
        return PreprocessedDocument(
            document_id=document_id,
            cleaned_text=cleaned,
            language=language,
            chunks=chunks,
            word_count=len(cleaned.split()),
        )
