"""
QueryPlanningAgent: converts a natural language question to Cypher and executes it.
Implements the /query API stub.
"""
from app.ai.anthropic_client import anthropic_client
from app.graph.neo4j_client import neo4j_client
from app.logger import get_logger

logger = get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """\
You are a Cypher query expert for Neo4j knowledge graphs.
Given a natural language question, generate a Cypher query.

Graph schema:
- All entity nodes have these properties: pg_id (UUID), name (string), entity_type (string), confidence (float), document_id (string)
- Entity labels are PascalCase versions of entity_type (e.g. Company, Person, Technology, Product, Location, Contract, Policy, Regulation)
- All relationships have type RELATES with property type (string, e.g. WORKS_FOR, OWNS, USES, BELONGS_TO, DEPENDS_ON)

Return ONLY valid Cypher. No markdown fences. No explanation. No comments."""


class QueryPlanningAgent:
    """Converts natural language to Cypher and executes it against Neo4j."""

    async def plan_and_execute(self, query: str, schema_hint: str | None = None) -> dict:
        """
        1. Use Claude Haiku to generate Cypher from the question
        2. Execute the Cypher via neo4j_client
        3. Return {query, cypher, results, error?}
        """
        prompt = f"Question: {query}"
        if schema_hint:
            prompt += f"\nAdditional context: {schema_hint}"
        prompt += "\nCypher:"

        try:
            raw_cypher = await anthropic_client.complete(
                prompt,
                model=MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
            )
            cypher = raw_cypher.strip().strip("`").strip()
            # Remove "cypher" language hint if present
            if cypher.lower().startswith("cypher"):
                cypher = cypher[6:].strip()
        except Exception as exc:
            logger.error("Claude API error generating Cypher: %s", exc)
            return {"query": query, "cypher": None, "results": [], "error": str(exc)}

        logger.info("Generated Cypher: %s", cypher)

        try:
            results = await neo4j_client.run(cypher)
        except RuntimeError:
            return {
                "query": query,
                "cypher": cypher,
                "results": [],
                "error": "Neo4j not available",
            }
        except Exception as exc:
            logger.warning("Cypher execution error: %s", exc)
            return {
                "query": query,
                "cypher": cypher,
                "results": [],
                "error": f"Cypher error: {exc}",
            }

        return {"query": query, "cypher": cypher, "results": results, "error": None}


query_planning_agent = QueryPlanningAgent()
