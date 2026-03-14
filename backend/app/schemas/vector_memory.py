"""
Pydantic schemas for the vector memory API.
"""
from pydantic import BaseModel, Field


class EmbedDocumentResponse(BaseModel):
    document_id: str
    chunks_created: int
    model_used: str
    already_embedded: bool = False


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    text: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    chunk_index: int
    token_count: int
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SearchResultItem]
