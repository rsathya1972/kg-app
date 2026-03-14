from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    mode: str = "natural_language"   # "natural_language" | "cypher" | "sparql"
    limit: int = 50
    explain: bool = False            # return Cypher translation alongside results


class QueryResultItem(BaseModel):
    data: dict
    score: float | None = None


class QueryResponse(BaseModel):
    query: str
    cypher: str | None = None        # populated when explain=True
    results: list[QueryResultItem]
    total: int
    execution_ms: int | None = None
