"""
Event extraction: identifies events (actions, occurrences) in text.
Stub — lower priority than entity/relation extraction.
"""
from app.extraction.base import BaseExtractor, ExtractionResult
from app.logger import get_logger

logger = get_logger(__name__)


class EventExtractor(BaseExtractor):
    """Extracts events (actions, occurrences) from text."""

    async def extract(self, document_id: str, text: str) -> ExtractionResult:
        logger.info("Event extraction requested for document: %s", document_id)
        raise NotImplementedError(
            "EventExtractor is a placeholder for future implementation."
        )
