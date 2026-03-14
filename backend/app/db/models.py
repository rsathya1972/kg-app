"""
SQLAlchemy ORM models for kg-app.

Tables:
  documents                — ingested raw documents
  chunk_embeddings         — per-chunk OpenAI embeddings (pgvector)
  extracted_entities       — AI-extracted named entities per document
  extracted_relationships  — AI-extracted entity relationships per document
  ontology_versions        — AI-discovered domain ontology snapshots (versioned)
"""
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False, default="text/plain")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language: Mapped[str] = mapped_column(String, nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    chunks: Mapped[list["ChunkEmbedding"]] = relationship(
        "ChunkEmbedding",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    entities: Mapped[list["ExtractedEntity"]] = relationship(
        "ExtractedEntity",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    relationships: Mapped[list["ExtractedRelationship"]] = relationship(
        "ExtractedRelationship",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id!r} filename={self.filename!r}>"


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<ChunkEmbedding id={self.id!r} doc={self.document_id!r} idx={self.chunk_index}>"


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    attributes_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_chunk: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    document: Mapped["Document"] = relationship("Document", back_populates="entities")

    def __repr__(self) -> str:
        return f"<ExtractedEntity id={self.id!r} type={self.entity_type!r} name={self.name!r}>"


class ExtractedRelationship(Base):
    __tablename__ = "extracted_relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    # Soft references — no FK constraint so relationships survive entity re-extraction
    source_entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    target_entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_entity_name: Mapped[str] = mapped_column(String, nullable=False)
    target_entity_name: Mapped[str] = mapped_column(String, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    document: Mapped["Document"] = relationship("Document", back_populates="relationships")

    def __repr__(self) -> str:
        return (
            f"<ExtractedRelationship id={self.id!r} "
            f"{self.source_entity_name!r} -{self.relationship_type}-> {self.target_entity_name!r}>"
        )


class OntologyVersion(Base):
    __tablename__ = "ontology_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Nullable FK — ontology versions survive document deletion (SET NULL)
    document_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    domain_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    ontology_json: Mapped[str] = mapped_column(Text, nullable=False)
    classes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relationships_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_used: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    def __repr__(self) -> str:
        return f"<OntologyVersion id={self.id!r} v{self.version} doc={self.document_id!r}>"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    # Nullable FK — run history survives document deletion (SET NULL)
    document_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    # "pending" | "running" | "completed" | "failed"
    current_step: Mapped[str | None] = mapped_column(String, nullable=True)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON list of {step_name, status, started_at, completed_at, output_summary, error}
    decisions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON list of {agent, message, timestamp}
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id!r} doc={self.document_id!r} status={self.status!r}>"


# ── Knowledge Evolution ───────────────────────────────────────────────────────


class KnowledgeIssue(Base):
    """A quality issue detected in the knowledge graph by the evolution engine."""

    __tablename__ = "knowledge_issues"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    issue_type: Mapped[str] = mapped_column(String, nullable=False)
    # "low_confidence_entity" | "low_confidence_relationship" | "duplicate_entity"
    # | "orphan_entity" | "unknown_entity_type" | "sparse_relationships"
    severity: Mapped[str] = mapped_column(String, nullable=False)
    # "error" | "warning" | "info"
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    relationship_id: Mapped[str | None] = mapped_column(String, nullable=True)
    document_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    # "open" | "resolved" | "dismissed"
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    def __repr__(self) -> str:
        return f"<KnowledgeIssue id={self.id!r} type={self.issue_type!r} severity={self.severity!r}>"


class OntologyProposal(Base):
    """An AI-generated proposal to evolve the knowledge graph ontology."""

    __tablename__ = "ontology_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    proposal_type: Mapped[str] = mapped_column(String, nullable=False)
    # "add_class" | "merge_class" | "add_relationship" | "rename_class"
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    # "pending" | "applied" | "dismissed"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<OntologyProposal id={self.id!r} type={self.proposal_type!r} status={self.status!r}>"
