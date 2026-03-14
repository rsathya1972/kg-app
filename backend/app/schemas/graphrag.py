from pydantic import BaseModel


class GraphRAGRequest(BaseModel):
    question: str
    top_k: int = 5
    max_hops: int = 2


class ReasoningStep(BaseModel):
    step: str           # "ontology_matching" | "graph_traversal" | "vector_retrieval" | "synthesis"
    description: str
    result_count: int | None = None
    detail: str | None = None


class GraphRAGNode(BaseModel):
    id: str
    name: str
    entity_type: str
    labels: list[str]
    confidence: float | None = None


class GraphRAGEdge(BaseModel):
    id: str
    type: str
    source_id: str
    target_id: str
    source_name: str | None = None
    target_name: str | None = None


class GraphRAGChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    text: str
    similarity_score: float


class GraphRAGResponse(BaseModel):
    question: str
    answer: str
    reasoning_trace: list[ReasoningStep]
    ontology_classes: list[str]
    graph_nodes: list[GraphRAGNode]
    graph_edges: list[GraphRAGEdge]
    document_chunks: list[GraphRAGChunk]
    cypher_used: str | None = None
    error: str | None = None
