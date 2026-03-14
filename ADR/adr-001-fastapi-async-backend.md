# ADR-001: FastAPI with Native Async

**Date**: 2026-01-15
**Status**: Accepted
**Supersedes**: —

---

## Context

The backend must handle concurrent document ingestion, multi-step AI pipeline execution (entity extraction, relationship extraction, graph writing), and real-time SSE progress streaming — all simultaneously. The AI pipeline makes multiple external API calls (Claude, OpenAI, Neo4j, PostgreSQL) that are inherently I/O-bound.

## Decision

Use **FastAPI** as the web framework with **async/await** throughout (`async def` route handlers, `AsyncSession` for SQLAlchemy, `run_in_executor` for blocking calls).

## Rationale

- FastAPI is built on Starlette/anyio which provides real async I/O — not just thread-pool concurrency
- Pydantic v2 is native for request validation and response serialization (FastAPI's first-class citizen)
- Auto-generated OpenAPI docs at `/docs` — zero extra work
- SSE streaming is first-class via `StreamingResponse`
- `asyncpg` (PostgreSQL) and `neo4j` Python driver both have async APIs

## Consequences

- All route handlers must be `async def`
- Blocking operations (some sync library calls) must be wrapped with `run_sync()` from `backend/app/utils/async_utils.py`
- The Anthropic Python SDK v0.40 is synchronous — wrapped via `run_sync()` in `anthropic_client.py`
- Tests require `pytest-asyncio`
