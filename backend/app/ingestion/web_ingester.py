"""
Web-based ingester: fetches and extracts text from URLs.
Stub — full implementation in a later step.
"""
import uuid

from app.ingestion.base import BaseIngester, IngestedDocument
from app.logger import get_logger

logger = get_logger(__name__)


class WebIngester(BaseIngester):
    """Ingests documents by fetching content from URLs."""

    async def can_handle(self, source: str) -> bool:
        return source.startswith("http://") or source.startswith("https://")

    async def ingest(self, source: str, metadata: dict | None = None) -> IngestedDocument:
        logger.info("Web ingestion requested for: %s", source)
        raise NotImplementedError(
            "WebIngester is not yet implemented. "
            "Will use httpx + html-to-text extraction in a later step."
        )
