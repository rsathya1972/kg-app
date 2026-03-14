"""
Graph writer: creates nodes and edges in Neo4j from extracted entities and relationships.
Uses MERGE for idempotency — safe to call multiple times on the same document.
"""
from app.db.models import ExtractedEntity, ExtractedRelationship
from app.graph.neo4j_client import neo4j_client
from app.logger import get_logger

logger = get_logger(__name__)


def _safe_label(entity_type: str) -> str:
    """Convert entity_type string to a safe Neo4j label (PascalCase, no spaces/special chars)."""
    parts = entity_type.replace("-", "_").replace(" ", "_").split("_")
    return "".join(w.capitalize() for w in parts if w) or "Entity"


class GraphBuilderService:
    """Writes entities and relationships to Neo4j as nodes and edges."""

    async def build(
        self,
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship],
    ) -> dict:
        """
        MERGE entities as nodes and relationships as edges in Neo4j.

        Returns:
            dict with nodes_created, nodes_updated, edges_created, edges_updated counts.
        """
        nodes_created = 0
        nodes_updated = 0
        edges_created = 0
        edges_updated = 0

        # MERGE each entity as a labeled Neo4j node keyed by pg_id
        for entity in entities:
            label = _safe_label(entity.entity_type)
            result = await neo4j_client.run(
                f"""
                MERGE (n:{label} {{pg_id: $pg_id}})
                ON CREATE SET
                    n.name = $name,
                    n.document_id = $doc_id,
                    n.attributes = $attrs,
                    n.confidence = $conf,
                    n.entity_type = $entity_type,
                    n.was_created = true
                ON MATCH SET
                    n.name = $name,
                    n.document_id = $doc_id,
                    n.attributes = $attrs,
                    n.confidence = $conf,
                    n.entity_type = $entity_type,
                    n.was_created = false
                RETURN n.was_created AS was_created
                """,
                {
                    "pg_id": entity.id,
                    "name": entity.name,
                    "doc_id": entity.document_id,
                    "attrs": entity.attributes_json,
                    "conf": entity.confidence,
                    "entity_type": entity.entity_type,
                },
            )
            if result and result[0].get("was_created"):
                nodes_created += 1
            else:
                nodes_updated += 1

        logger.info(
            "Neo4j nodes: %d created, %d updated for document %s",
            nodes_created, nodes_updated,
            entities[0].document_id if entities else "unknown",
        )

        # MERGE each relationship as an edge between the two entity nodes
        for rel in relationships:
            if not rel.source_entity_id or not rel.target_entity_id:
                continue
            result = await neo4j_client.run(
                """
                MATCH (src {pg_id: $src_id})
                MATCH (tgt {pg_id: $tgt_id})
                MERGE (src)-[r:RELATES {pg_id: $pg_id}]->(tgt)
                ON CREATE SET
                    r.type = $rel_type,
                    r.confidence = $conf,
                    r.evidence = $evidence,
                    r.was_created = true
                ON MATCH SET
                    r.type = $rel_type,
                    r.confidence = $conf,
                    r.evidence = $evidence,
                    r.was_created = false
                RETURN r.was_created AS was_created
                """,
                {
                    "src_id": rel.source_entity_id,
                    "tgt_id": rel.target_entity_id,
                    "pg_id": rel.id,
                    "rel_type": rel.relationship_type,
                    "conf": rel.confidence,
                    "evidence": rel.evidence_text,
                },
            )
            if result and result[0].get("was_created"):
                edges_created += 1
            else:
                edges_updated += 1

        logger.info(
            "Neo4j edges: %d created, %d updated",
            edges_created, edges_updated,
        )

        return {
            "nodes_created": nodes_created,
            "nodes_updated": nodes_updated,
            "edges_created": edges_created,
            "edges_updated": edges_updated,
        }


# Module-level singleton
graph_builder = GraphBuilderService()
