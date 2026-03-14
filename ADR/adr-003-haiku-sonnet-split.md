# ADR-003: Claude Model Split — Haiku for Extraction, Sonnet for Reasoning

**Date**: 2026-01-20
**Status**: Accepted
**Supersedes**: —

---

## Context

The AI pipeline makes multiple Claude API calls per document processing run. Some calls are bulk/mechanical (entity extraction over many chunks), others require sophisticated reasoning (answer generation, ontology analysis). Using the same model for both wastes money on bulk tasks or sacrifices quality on reasoning tasks.

## Decision

Use **`claude-haiku-4-5-20251001`** for extraction/parsing/classification tasks.
Use **`claude-sonnet-4-6`** for generation/reasoning/synthesis tasks.

## Rationale

| Task | Model | Reason |
|------|-------|--------|
| Entity extraction (per chunk) | Haiku | Bulk calls, structured JSON output, speed matters |
| Relationship extraction (per chunk) | Haiku | Same as above |
| NL → Cypher translation | Haiku | Well-structured task, short output |
| Ontology proposal generation | Haiku | Classification/labeling task |
| Knowledge issue reasoning | Haiku | Short rationale strings |
| GraphRAG answer synthesis | Sonnet | Quality matters, user-facing output |
| Ontology alignment (planned) | Sonnet | Nuanced semantic judgment |
| NL → StructuredQuery (planned) | Sonnet | Complex intent parsing |

## Consequences

- Cost scales with document size for Haiku calls (extraction)
- Sonnet calls are used sparingly — only for user-facing, quality-critical outputs
- Model constants defined in `backend/app/ai/anthropic_client.py`:
  ```python
  HAIKU = "claude-haiku-4-5-20251001"
  SONNET = "claude-sonnet-4-6"
  ```
- Update this ADR and `PROMPTS.md` if the model selection changes for any prompt
