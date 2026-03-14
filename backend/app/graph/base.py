"""
Graph dataclasses: Node, Edge, GraphResult.
"""
from dataclasses import dataclass, field
import uuid


@dataclass
class Node:
    """A node in the knowledge graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    labels: list[str] = field(default_factory=list)   # Neo4j node labels
    properties: dict = field(default_factory=dict)


@dataclass
class Edge:
    """A directed edge (relationship) in the knowledge graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""               # Relationship type (e.g. "WORKS_FOR")
    source_id: str = ""
    target_id: str = ""
    properties: dict = field(default_factory=dict)


@dataclass
class GraphResult:
    """The result of a graph read or write operation."""
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)
