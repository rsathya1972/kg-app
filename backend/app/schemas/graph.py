from pydantic import BaseModel


class NodeResponse(BaseModel):
    id: str
    labels: list[str]
    properties: dict


class EdgeResponse(BaseModel):
    id: str
    type: str
    source_id: str
    target_id: str
    properties: dict | None = None


class GraphResponse(BaseModel):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
    node_count: int
    edge_count: int


class GraphWriteRequest(BaseModel):
    document_id: str
    overwrite: bool = False


class GraphWriteResponse(BaseModel):
    nodes_created: int
    edges_created: int
    nodes_updated: int
    edges_updated: int
