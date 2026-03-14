"""
Natural language query parser: converts NL to a StructuredQuery using AI.
Stub — AI call wired in Step 7.
"""
from app.logger import get_logger
from app.query.base import StructuredQuery

logger = get_logger(__name__)

NL_PARSE_PROMPT = """
Parse the following natural language query into a structured graph query.
Return ONLY valid JSON:
{
  "intent": "find|count|relate|path",
  "entity_types": ["..."],
  "filters": {"property": "value"},
  "relations": ["RELATION_TYPE"],
  "limit": 50
}

Query: {query}
"""


class NLParser:
    """Converts natural language questions into StructuredQuery objects."""

    def __init__(self, provider: str = "anthropic") -> None:
        self.provider = provider

    async def parse(self, query: str) -> StructuredQuery:
        """
        Parse a natural language query.

        Args:
            query: Natural language question (e.g. "Who works for Acme Corp?")

        Returns:
            StructuredQuery

        Raises:
            NotImplementedError: Until AI client is wired.
        """
        logger.info("NL query parse requested: %s", query[:80])
        raise NotImplementedError(
            "NLParser.parse() is a stub. Wire up AI client in Step 7."
        )
