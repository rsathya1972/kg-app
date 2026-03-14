"""
Ingester registry: maps source types to the appropriate BaseIngester.
"""
from app.ingestion.base import BaseIngester, IngestedDocument
from app.ingestion.file_ingester import FileIngester
from app.ingestion.web_ingester import WebIngester
from app.logger import get_logger

logger = get_logger(__name__)

_INGESTERS: list[BaseIngester] = [
    FileIngester(),
    WebIngester(),
]


async def ingest(source: str, metadata: dict | None = None) -> IngestedDocument:
    """
    Route a source to the first ingester that can handle it.

    Args:
        source: File path, URL, or other source identifier.
        metadata: Optional metadata to attach to the document.

    Returns:
        IngestedDocument

    Raises:
        ValueError: If no ingester can handle the source.
    """
    for ingester in _INGESTERS:
        if await ingester.can_handle(source):
            logger.info("Using %s for source: %s", type(ingester).__name__, source)
            return await ingester.ingest(source, metadata)
    raise ValueError(f"No ingester available for source: {source}")
