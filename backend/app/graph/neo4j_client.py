"""
Neo4j async driver wrapper.
"""
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class Neo4jClient:
    """Wrapper around the Neo4j async Python driver."""

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Open the Neo4j driver connection and verify connectivity."""
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        await self._driver.verify_connectivity()
        logger.info("Neo4j connected: %s", settings.NEO4J_URI)

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    async def run(self, cypher: str, parameters: dict | None = None) -> list[dict]:
        """
        Execute a Cypher query and return results as a list of dicts.

        Args:
            cypher: Cypher query string.
            parameters: Optional query parameters.

        Returns:
            List of result records as dicts.
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        async with self._driver.session() as session:
            result = await session.run(cypher, parameters or {})
            return [record.data() async for record in result]

    async def health_check(self) -> bool:
        """Return True if the Neo4j instance is reachable."""
        if not self._driver:
            return False
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False


# Module-level singleton
neo4j_client = Neo4jClient()
