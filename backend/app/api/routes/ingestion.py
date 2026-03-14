"""
Ingestion API routes — store documents for downstream processing.

POST /ingest          — ingest raw text
POST /ingest/upload   — upload a file (TXT, PDF, DOCX)
GET  /ingest          — list all documents
GET  /ingest/{id}     — get a single document
DELETE /ingest/{id}   — delete a document and its embeddings
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document
from app.logger import get_logger
from app.schemas.ingestion import IngestRequest, IngestedDocumentResponse

router = APIRouter(prefix="/ingest", tags=["Ingestion"])
logger = get_logger(__name__)


def _doc_to_response(doc: Document) -> IngestedDocumentResponse:
    return IngestedDocumentResponse(
        id=doc.id,
        source_type="file" if doc.filename != "raw_text" else "text",
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_kb=round(len(doc.raw_text.encode()) / 1024, 2),
        word_count=doc.word_count,
        language=doc.language,
        ingested_at=doc.created_at,
        status="ingested",
    )


@router.post("", response_model=IngestedDocumentResponse, status_code=201)
async def ingest_document(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestedDocumentResponse:
    """
    Ingest a document from raw text.
    Set source_type='text' and provide raw_text.
    """
    if not request.raw_text:
        raise HTTPException(
            status_code=422,
            detail="raw_text is required for source_type='text'. "
                   "Use POST /ingest/upload for file ingestion.",
        )

    text = request.raw_text.strip()
    word_count = len(text.split())

    doc = Document(
        id=str(uuid.uuid4()),
        filename=request.metadata.get("filename", "raw_text") if request.metadata else "raw_text",
        mime_type="text/plain",
        raw_text=text,
        word_count=word_count,
        language="en",
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info("Ingested raw text document id=%s word_count=%d", doc.id, word_count)
    return _doc_to_response(doc)


@router.post("/upload", response_model=IngestedDocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> IngestedDocumentResponse:
    """
    Upload a TXT, PDF, or DOCX file and ingest its text content.
    """
    from app.ingestion.registry import ingest as registry_ingest

    content = await file.read()
    filename = file.filename or "upload.txt"
    mime_type = file.content_type or "text/plain"

    # Write to a temp file so the FileIngester can read it
    import tempfile, os
    suffix = os.path.splitext(filename)[1] or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        ingested = await registry_ingest(tmp_path, metadata={"filename": filename})
    finally:
        os.unlink(tmp_path)

    text = ingested.raw_text.strip()
    word_count = len(text.split())

    doc = Document(
        id=str(uuid.uuid4()),
        filename=filename,
        mime_type=mime_type,
        raw_text=text,
        word_count=word_count,
        language="en",
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info("Ingested file %r id=%s word_count=%d", filename, doc.id, word_count)
    return _doc_to_response(doc)


@router.get("", response_model=list[IngestedDocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
) -> list[IngestedDocumentResponse]:
    """List all ingested documents (newest first)."""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [_doc_to_response(d) for d in docs]


@router.get("/{document_id}", response_model=IngestedDocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> IngestedDocumentResponse:
    """Get a single ingested document by ID."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id!r} not found")
    return _doc_to_response(doc)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document and its chunk embeddings (cascade)."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id!r} not found")
    await db.delete(doc)
    await db.commit()
    logger.info("Deleted document id=%s", document_id)
