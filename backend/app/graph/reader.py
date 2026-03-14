"""
Graph reader: queries Neo4j for nodes and edges.
"""
from app.graph.neo4j_client import neo4j_client
from app.logger import get_logger

logger = get_logger(__name__)


class GraphReader:
    """Queries the Neo4j knowledge graph."""

    async def get_neighborhood(self, pg_id: str, depth: int = 2) -> dict:
        """
        Return all nodes and edges within `depth` hops of the entity with the given pg_id.
        """
        rows = await neo4j_client.run(
            """
            MATCH (start {pg_id: $pg_id})
            OPTIONAL MATCH path = (start)-[*0..$depth]-(neighbor)
            WITH COLLECT(DISTINCT nodes(path)) AS path_nodes_list,
                 COLLECT(DISTINCT relationships(path)) AS path_rels_list
            WITH [n IN apoc.coll.flatten(path_nodes_list) | {
                id: n.pg_id,
                labels: labels(n),
                properties: {
                    name: n.name,
                    entity_type: n.entity_type,
                    confidence: n.confidence,
                    attributes: n.attributes
                }
            }] AS nodes,
            [r IN apoc.coll.flatten(path_rels_list) | {
                id: r.pg_id,
                type: r.type,
                source_id: startNode(r).pg_id,
                target_id: endNode(r).pg_id
            }] AS edges
            RETURN nodes, edges
            """,
            {"pg_id": pg_id, "depth": depth},
        )
        if not rows:
            return {"nodes": [], "edges": []}
        return {
            "nodes": rows[0].get("nodes", []),
            "edges": rows[0].get("edges", []),
        }

    async def get_document_graph(self, document_id: str) -> dict:
        """Return all nodes and edges for a given document_id."""
        node_rows = await neo4j_client.run(
            """
            MATCH (n {document_id: $doc_id})
            RETURN n.pg_id AS id, labels(n) AS labels,
                   n.name AS name, n.entity_type AS entity_type,
                   n.confidence AS confidence, n.attributes AS attributes
            """,
            {"doc_id": document_id},
        )
        edge_rows = await neo4j_client.run(
            """
            MATCH (src {document_id: $doc_id})-[r]->(tgt {document_id: $doc_id})
            RETURN r.pg_id AS id, r.type AS type,
                   src.pg_id AS source_id, tgt.pg_id AS target_id
            """,
            {"doc_id": document_id},
        )
        nodes = [
            {
                "id": r["id"],
                "labels": r["labels"],
                "properties": {
                    "name": r["name"],
                    "entity_type": r["entity_type"],
                    "confidence": r["confidence"],
                    "attributes": r["attributes"],
                },
            }
            for r in node_rows
            if r.get("id")
        ]
        edges = [
            {
                "id": r.get("id") or f"{r['source_id']}-{r['target_id']}",
                "type": r["type"],
                "source_id": r["source_id"],
                "target_id": r["target_id"],
                "properties": {},
            }
            for r in edge_rows
            if r.get("source_id") and r.get("target_id")
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    async def get_stats(self) -> dict:
        """Return basic graph statistics: node count, edge count, label distribution."""
        label_rows = await neo4j_client.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC"
        )
        edge_rows = await neo4j_client.run(
            "MATCH ()-[r]->() RETURN count(r) AS total"
        )
        return {
            "node_count": sum(r["cnt"] for r in label_rows),
            "edge_count": edge_rows[0]["total"] if edge_rows else 0,
            "label_distribution": {r["label"]: r["cnt"] for r in label_rows if r.get("label")},
        }


# Module-level singleton
graph_reader = GraphReader()
