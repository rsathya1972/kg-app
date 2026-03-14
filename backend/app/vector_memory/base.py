"""
Core dataclasses for the vector memory module.
"""
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    filename: str
    text: str
    similarity_score: float          # 0.0–1.0 (cosine similarity)
    chunk_index: int
    token_count: int
    metadata: dict = field(default_factory=dict)


@dataclass
class EmbedResult:
    document_id: str
    chunks_created: int
    model_used: str
    already_embedded: bool = False   # True if previously embedded (idempotent re-run)
