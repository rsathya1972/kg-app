"""
Query dataclasses: QueryRequest and QueryResult.
"""
from dataclasses import dataclass, field


@dataclass
class StructuredQuery:
    """Intermediate structured query representation (parsed from natural language)."""
    intent: str = ""             # "find", "count", "relate", "path"
    entity_types: list[str] = field(default_factory=list)
    filters: dict = field(default_factory=dict)
    relations: list[str] = field(default_factory=list)
    limit: int = 50
    raw_nl: str = ""             # Original natural language query


@dataclass
class QueryResultItem:
    """A single result row from a graph query."""
    data: dict = field(default_factory=dict)
    score: float | None = None


@dataclass
class QueryResult:
    """Full result of a query execution."""
    query: str
    cypher: str | None = None    # Cypher used (if applicable)
    results: list[QueryResultItem] = field(default_factory=list)
    total: int = 0
    execution_ms: int | None = None
