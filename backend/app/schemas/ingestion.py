from datetime import datetime
from pydantic import BaseModel


class IngestRequest(BaseModel):
    source_type: str = "file"        # "file" | "url" | "text"
    source_path: str | None = None   # file path or URL
    raw_text: str | None = None      # direct text input
    metadata: dict | None = None


class IngestedDocumentResponse(BaseModel):
    id: str
    source_type: str
    filename: str | None
    mime_type: str | None
    size_kb: float | None
    word_count: int | None
    language: str | None
    ingested_at: datetime
    status: str                      # "pending" | "preprocessed" | "extracted"
