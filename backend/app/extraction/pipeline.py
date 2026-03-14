"""
Extraction pipeline: orchestrates preprocessing → entity extraction → relation extraction.
"""
from app.extraction.base import ExtractionResult
from app.extraction.entity_extractor import EntityExtractor
from app.extraction.relation_extractor import RelationExtractor
from app.logger import get_logger
from app.preprocessing.base import PreprocessedDocument
from app.preprocessing.text_cleaner import TextCleaner
from app.preprocessing.chunker import SlidingWindowChunker
from app.preprocessing.language_detector import detect_language

logger = get_logger(__name__)


class ExtractionPipeline:
    """
    Full extraction pipeline:
    1. Clean raw text
    2. Detect language
    3. Chunk into AI-sized pieces
    4. Extract entities per chunk
    5. Extract relations from entities
    6. Merge results

    All AI steps are stubs until wired in a later step.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        extract_relations: bool = True,
    ) -> None:
        self.cleaner = TextCleaner()
        self.chunker = SlidingWindowChunker()
        self.entity_extractor = EntityExtractor(provider=provider)
        self.relation_extractor = RelationExtractor(provider=provider)
        self.extract_relations = extract_relations

    async def run(self, document_id: str, raw_text: str) -> ExtractionResult:
        """
        Run the full pipeline on raw document text.

        Args:
            document_id: ID of the source document.
            raw_text: Unprocessed document text.

        Returns:
            Merged ExtractionResult across all chunks.
        """
        logger.info("Starting extraction pipeline for document: %s", document_id)

        cleaned = self.cleaner.clean(raw_text)
        language = detect_language(cleaned)
        chunks = self.chunker.chunk(cleaned)

        logger.info(
            "Document %s: %d chunks, language=%s",
            document_id, len(chunks), language or "unknown",
        )

        # Stub: entity and relation extraction are not yet implemented
        raise NotImplementedError(
            "ExtractionPipeline.run() is a stub. "
            "Implement per-chunk AI calls and result merging in a later step."
        )

    def _merge_results(self, results: list[ExtractionResult]) -> ExtractionResult:
        """Merge extraction results from multiple chunks into one."""
        if not results:
            return ExtractionResult(document_id="unknown")
        merged = ExtractionResult(document_id=results[0].document_id)
        for r in results:
            merged.entities.extend(r.entities)
            merged.relations.extend(r.relations)
        return merged
