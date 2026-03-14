"""
Query executor: runs Cypher against Neo4j and returns QueryResult.
Stub — wired in Step 7.
"""
import time

from app.logger import get_logger
from app.query.base import QueryResult

logger = get_logger(__name__)


class QueryExecutor:
    """Executes Cypher queries against Neo4j and formats results."""

    async def execute(self, cypher: str, parameters: dict | None = None) -> QueryResult:
        """
        Run a Cypher query and return structured results.

        Args:
            cypher: Cypher query string.
            parameters: Optional Cypher parameters.

        Returns:
            QueryResult

        Raises:
            NotImplementedError: Until Neo4j client is wired.
        """
        start = time.time()
        logger.info("Executing Cypher: %s", cypher[:120])
        raise NotImplementedError(
            "QueryExecutor.execute() is a stub. Wire up Neo4j client in Step 7."
        )
