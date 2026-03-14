from fastapi import APIRouter
from app.schemas.extraction import ExtractRequest
from app.logger import get_logger

router = APIRouter(prefix="/extract", tags=["Extraction"])
logger = get_logger(__name__)


@router.post("", status_code=501)
async def extract(request: ExtractRequest):
    """
    Run entity and relation extraction on an ingested document.
    Uses the AI extraction pipeline (Claude / OpenAI).
    """
    logger.info("Extract request: document_id=%s", request.document_id)
    return {"status": "not_implemented", "module": "extraction"}


@router.get("/{document_id}", status_code=501)
async def get_extraction_result(document_id: str):
    """Get the extraction result for a specific document."""
    return {"status": "not_implemented", "module": "extraction", "document_id": document_id}
