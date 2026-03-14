"""
GraphRAGService: combines ontology reasoning, graph traversal, and vector search
to answer natural language questions about the knowledge graph.

Pipeline:
  1. Identify relevant ontology classes from the question (Claude Haiku)
  2. Traverse Neo4j graph for matching nodes + 1-hop neighborhood
  3. Retrieve top-k semantically similar document chunks (pgvector)
  4. Synthesize a grounded answer (Claude Sonnet) with full reasoning trace
"""
import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anthropic_client import anthropic_client
from app.db.models import OntologyVersion
from app.graph.neo4j_client import neo4j_client
from app.logger import get_logger
from app.ontology.manager import ontology_manager
from app.schemas.graphrag import (
    GraphRAGChunk,
    GraphRAGEdge,
    GraphRAGNode,
    GraphRAGResponse,
    ReasoningStep,
)
from app.vector_memory.embedding_service import embedding_service

logger = get_logger(__name__)

# Maximum nodes/edges returned from graph traversal to keep context manageable
_MAX_NODES = 60
_MAX_EDGES = 80


class GraphRAGService:

    # ── Step 1: Ontology class identification ────────────────────────────────

    async def _collect_class_names(self, db: AsyncSession) -> list[str]:
        """
        Merge class names from:
          - In-memory OntologyManager defaults (Entity, Person, Organization …)
          - Discovered classes stored in OntologyVersion rows in PostgreSQL
        Also fetches the actual entity_type labels present in Neo4j so the
        LLM has ground-truth class names that match the stored data.
        """
        names: set[str] = {c.name for c in ontology_manager.list_classes()}

        # Pull discovered class names from the latest ontology versions
        try:
            rows = await db.execute(select(OntologyVersion).order_by(OntologyVersion.created_at.desc()).limit(5))
            for version in rows.scalars().all():
                try:
                    content = json.loads(version.content_json)
                    for cls in content.get("classes", []):
                        if cls.get("name"):
                            names.add(cls["name"])
                except Exception:
                    pass
        except Exception:
            pass

        # Add entity types actually present in Neo4j
        try:
            label_rows = await neo4j_client.run(
                "MATCH (n) WHERE n.entity_type IS NOT NULL "
                "RETURN DISTINCT n.entity_type AS et LIMIT 50"
            )
            for r in label_rows:
                if r.get("et"):
                    names.add(r["et"])
        except Exception:
            pass

        return sorted(names)

    async def _identify_ontology_classes(
        self, question: str, available_classes: list[str]
    ) -> list[str]:
        """Ask Claude Haiku which ontology classes are relevant to the question."""
        if not available_classes:
            return []

        classes_str = ", ".join(available_classes)
        system = (
            "You identify which ontology entity class names are relevant to a natural language question. "
            "Return ONLY a JSON array of class name strings chosen from the provided list. "
            "If the question asks about companies/organizations, include Organization and Company. "
            "Return [] if truly none apply. No markdown, no explanation."
        )
        prompt = f"Available classes: [{classes_str}]\n\nQuestion: {question}\n\nRelevant classes (JSON array):"

        raw = await anthropic_client.complete(
            prompt, model="claude-haiku-4-5-20251001", max_tokens=256, system=system
        )
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            result = json.loads(cleaned)
            if isinstance(result, list):
                return [str(c) for c in result if c]
        except Exception:
            pass
        # Fallback: return top 3 available classes
        return available_classes[:3]

    # ── Step 2: Graph traversal ───────────────────────────────────────────────

    async def _traverse_graph(
        self, ontology_classes: list[str], max_hops: int
    ) -> tuple[list[GraphRAGNode], list[GraphRAGEdge], str]:
        """
        Find seed nodes matching the ontology classes and their neighborhood.
        Returns (nodes, edges, cypher_used).
        """
        if not ontology_classes:
            return [], [], ""

        # Lower-case class names for case-insensitive matching
        lower_classes = [c.lower() for c in ontology_classes]

        # Build WHERE clause: match entity_type (case-insensitive) OR Neo4j label
        cypher_seed = (
            "MATCH (n) "
            "WHERE toLower(n.entity_type) IN $types OR "
            "      any(l IN labels(n) WHERE toLower(l) IN $types) "
            f"RETURN n.pg_id AS id, n.name AS name, n.entity_type AS entity_type, "
            "labels(n) AS labels, n.confidence AS confidence "
            f"LIMIT {_MAX_NODES}"
        )

        cypher_edges = (
            "MATCH (src)-[r]->(tgt) "
            "WHERE (toLower(src.entity_type) IN $types OR any(l IN labels(src) WHERE toLower(l) IN $types)) "
            "   OR (toLower(tgt.entity_type) IN $types OR any(l IN labels(tgt) WHERE toLower(l) IN $types)) "
            "RETURN r.pg_id AS id, r.type AS rel_type, "
            "       src.pg_id AS source_id, tgt.pg_id AS target_id, "
            "       src.name AS source_name, tgt.name AS target_name "
            f"LIMIT {_MAX_EDGES}"
        )

        params = {"types": lower_classes}

        node_rows = await neo4j_client.run(cypher_seed, params)
        edge_rows = await neo4j_client.run(cypher_edges, params)

        # If no seed nodes found, fall back to returning everything (up to limit)
        if not node_rows:
            cypher_seed = (
                "MATCH (n) RETURN n.pg_id AS id, n.name AS name, "
                "n.entity_type AS entity_type, labels(n) AS labels, "
                f"n.confidence AS confidence LIMIT {_MAX_NODES}"
            )
            cypher_edges = (
                "MATCH (src)-[r]->(tgt) "
                "RETURN r.pg_id AS id, r.type AS rel_type, "
                "src.pg_id AS source_id, tgt.pg_id AS target_id, "
                "src.name AS source_name, tgt.name AS target_name "
                f"LIMIT {_MAX_EDGES}"
            )
            node_rows = await neo4j_client.run(cypher_seed)
            edge_rows = await neo4j_client.run(cypher_edges)
            params = {}

        nodes = [
            GraphRAGNode(
                id=r["id"] or "",
                name=r.get("name") or "(unnamed)",
                entity_type=r.get("entity_type") or "Unknown",
                labels=r.get("labels") or [],
                confidence=r.get("confidence"),
            )
            for r in node_rows
            if r.get("id")
        ]

        edges = [
            GraphRAGEdge(
                id=r.get("id") or f"{r.get('source_id')}-{r.get('target_id')}",
                type=r.get("rel_type") or "RELATES",
                source_id=r.get("source_id") or "",
                target_id=r.get("target_id") or "",
                source_name=r.get("source_name"),
                target_name=r.get("target_name"),
            )
            for r in edge_rows
            if r.get("source_id") and r.get("target_id")
        ]

        cypher_display = cypher_seed.replace("$types", str(lower_classes))
        return nodes, edges, cypher_display

    # ── Step 3: Vector retrieval ──────────────────────────────────────────────

    async def _vector_search(
        self, question: str, top_k: int, db: AsyncSession
    ) -> list[GraphRAGChunk]:
        try:
            results = await embedding_service.semantic_search(question, top_k, db)
            return [
                GraphRAGChunk(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    filename=r.filename,
                    text=r.text,
                    similarity_score=r.similarity_score,
                )
                for r in results
            ]
        except Exception as exc:
            logger.warning("Vector search failed (non-fatal): %s", exc)
            return []

    # ── Step 4: Answer synthesis ──────────────────────────────────────────────

    async def _synthesize(
        self,
        question: str,
        nodes: list[GraphRAGNode],
        edges: list[GraphRAGEdge],
        chunks: list[GraphRAGChunk],
        ontology_classes: list[str],
    ) -> str:
        # Build graph context
        graph_lines: list[str] = []
        if nodes:
            graph_lines.append("=== Knowledge Graph Entities ===")
            for n in nodes[:30]:
                graph_lines.append(f"- [{n.entity_type}] {n.name}")
        if edges:
            graph_lines.append("\n=== Graph Relationships ===")
            for e in edges[:30]:
                src = e.source_name or e.source_id
                tgt = e.target_name or e.target_id
                graph_lines.append(f"- {src} --[{e.type}]--> {tgt}")

        # Build vector context
        vector_lines: list[str] = []
        if chunks:
            vector_lines.append("=== Document Passages ===")
            for c in chunks:
                vector_lines.append(f"[{c.filename}, similarity={c.similarity_score:.2f}]\n{c.text}")

        context_parts = []
        if graph_lines:
            context_parts.append("\n".join(graph_lines))
        if vector_lines:
            context_parts.append("\n".join(vector_lines))

        if not context_parts:
            return (
                "I could not find relevant information in the knowledge graph or document corpus "
                "to answer this question. Try ingesting and processing documents first."
            )

        context = "\n\n".join(context_parts)
        system = (
            "You are a knowledge graph assistant. Answer questions using ONLY the provided "
            "graph entities, relationships, and document passages. "
            "Be factual and cite specific entities or passages when possible. "
            "If the context does not contain enough information, say so clearly. "
            "NEVER invent facts not present in the context."
        )
        prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

        return await anthropic_client.complete(
            prompt,
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
        )

    # ── Public entry point ────────────────────────────────────────────────────

    async def query(
        self,
        question: str,
        top_k: int,
        max_hops: int,
        db: AsyncSession,
    ) -> GraphRAGResponse:
        trace: list[ReasoningStep] = []
        error: str | None = None

        # Step 1 — ontology class identification
        available_classes = await self._collect_class_names(db)
        ontology_classes: list[str] = []
        try:
            ontology_classes = await self._identify_ontology_classes(question, available_classes)
            trace.append(ReasoningStep(
                step="ontology_matching",
                description="Identified relevant ontology classes for the question",
                result_count=len(ontology_classes),
                detail=f"Matched: {', '.join(ontology_classes) or 'none'} "
                       f"(from {len(available_classes)} available classes)",
            ))
        except Exception as exc:
            logger.warning("Ontology class identification failed: %s", exc)
            trace.append(ReasoningStep(
                step="ontology_matching",
                description="Ontology class identification failed",
                detail=str(exc),
            ))

        # Step 2 — graph traversal
        nodes: list[GraphRAGNode] = []
        edges: list[GraphRAGEdge] = []
        cypher_used: str | None = None
        try:
            nodes, edges, cypher_used = await self._traverse_graph(ontology_classes, max_hops)
            trace.append(ReasoningStep(
                step="graph_traversal",
                description="Traversed Neo4j knowledge graph for matching entities and relationships",
                result_count=len(nodes),
                detail=f"{len(nodes)} nodes, {len(edges)} edges retrieved "
                       f"(entity types: {', '.join(ontology_classes) or 'all'})",
            ))
        except Exception as exc:
            logger.warning("Graph traversal failed: %s", exc)
            trace.append(ReasoningStep(
                step="graph_traversal",
                description="Graph traversal failed (Neo4j may be unavailable)",
                detail=str(exc),
            ))

        # Step 3 — vector retrieval
        chunks: list[GraphRAGChunk] = []
        try:
            chunks = await self._vector_search(question, top_k, db)
            trace.append(ReasoningStep(
                step="vector_retrieval",
                description="Retrieved semantically similar document passages using pgvector",
                result_count=len(chunks),
                detail=f"Top-{top_k} chunks; best similarity: "
                       f"{chunks[0].similarity_score:.3f}" if chunks else "No embeddings found",
            ))
        except Exception as exc:
            logger.warning("Vector retrieval failed: %s", exc)
            trace.append(ReasoningStep(
                step="vector_retrieval",
                description="Vector retrieval failed",
                detail=str(exc),
            ))

        # Step 4 — synthesis
        answer = ""
        try:
            answer = await self._synthesize(question, nodes, edges, chunks, ontology_classes)
            trace.append(ReasoningStep(
                step="synthesis",
                description="Synthesized answer from graph entities, relationships, and document passages",
                result_count=None,
                detail=f"Used {len(nodes)} graph nodes, {len(edges)} edges, {len(chunks)} text chunks",
            ))
        except Exception as exc:
            error = str(exc)
            answer = f"Answer synthesis failed: {exc}"
            logger.error("GraphRAG synthesis error: %s", exc)
            trace.append(ReasoningStep(
                step="synthesis",
                description="Answer synthesis failed",
                detail=error,
            ))

        return GraphRAGResponse(
            question=question,
            answer=answer,
            reasoning_trace=trace,
            ontology_classes=ontology_classes,
            graph_nodes=nodes,
            graph_edges=edges,
            document_chunks=chunks,
            cypher_used=cypher_used,
            error=error,
        )


# Module-level singleton
graphrag_service = GraphRAGService()
