"""
Cypher query builder: converts a StructuredQuery into a Cypher string.
"""
from app.logger import get_logger
from app.query.base import StructuredQuery

logger = get_logger(__name__)


class CypherBuilder:
    """Builds Cypher queries from StructuredQuery objects."""

    def build(self, query: StructuredQuery) -> str:
        """
        Generate a Cypher query string from a StructuredQuery.

        Args:
            query: Parsed structured query.

        Returns:
            Cypher query string.

        Raises:
            NotImplementedError: Builder not yet implemented.
        """
        logger.debug("Building Cypher for intent: %s", query.intent)
        raise NotImplementedError(
            "CypherBuilder.build() is a stub. "
            "Implement Cypher generation templates in Step 7."
        )

    def _find_query(self, query: StructuredQuery) -> str:
        """Template for MATCH + RETURN queries."""
        labels = "|".join(query.entity_types) if query.entity_types else ""
        label_clause = f":{labels}" if labels else ""
        where_clauses = [
            f"n.{k} = '{v}'" for k, v in query.filters.items()
        ]
        where = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return f"MATCH (n{label_clause}){where} RETURN n LIMIT {query.limit}"
