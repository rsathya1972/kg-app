# Extraction Module

Extracts named entities and relationships from document text using Claude Haiku.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | Type definitions: `Entity`, `Relation`, `ExtractionResult`, `ENTITY_TYPES`, `RELATIONSHIP_TYPES` |
| `entity_extractor.py` | `EntityExtractionAgent` — NER via Claude Haiku |
| `relation_extractor.py` | `RelationExtractor` — relationship extraction via Claude Haiku |
| `event_extractor.py` | Stub — event extraction (not yet implemented) |

---

## How It Works

### Entity Extraction

1. Text is chunked by `SlidingWindowChunker` (600 tokens, 50 token overlap)
2. Each chunk is sent to Claude Haiku with PROMPT-001
3. Response JSON is parsed → `Entity` objects
4. Entities are deduplicated across chunks (highest confidence per name kept)
5. Results persisted to `extracted_entities` table

### Relationship Extraction

1. Takes extracted entity list + original text as input
2. Chunks text with the same SlidingWindowChunker
3. **Optimization**: skips chunks that contain fewer than 2 entity names (no point looking for relationships)
4. Each qualifying chunk sent to Claude Haiku with PROMPT-002
5. Response JSON parsed → `Relation` objects
6. Deduplication: highest-confidence per (source, type, target) triple kept
7. Results persisted to `extracted_relationships` table

---

## Key Classes

### `EntityExtractionAgent`

```python
agent = EntityExtractionAgent()
result: ExtractionResult = await agent.extract(text="...", document_id=uuid)
# result.entities: list[Entity]
# result.relations: []  ← empty, use RelationExtractor for these
```

### `RelationExtractor`

```python
extractor = RelationExtractor()
result: ExtractionResult = await extractor.extract(
    text="...",
    entities=[Entity(...)],  # from EntityExtractionAgent
    document_id=uuid
)
# result.relations: list[Relation]
```

---

## Supported Types

Defined as `frozenset` in `base.py` — **do not mutate at runtime**.

**Entity types** (8): `Company`, `Person`, `Product`, `Contract`, `Location`, `Technology`, `Policy`, `Regulation`

**Relationship types** (10): `WORKS_FOR`, `OWNS`, `USES`, `BELONGS_TO`, `RENEWS`, `EXPIRES_ON`, `LOCATED_IN`, `DEPENDS_ON`, `SELLS_TO`, `GOVERNED_BY`

---

## How to Extend

### Adding a new entity type

1. Add the type string to `ENTITY_TYPES` in `base.py`
2. Update PROMPT-001 in `entity_extractor.py` (the valid types list in the system prompt)
3. Update `PROMPTS.md` PROMPT-001 entity types list
4. Update `SCHEMA.md` Entity Types section
5. The new type will flow through to Neo4j automatically (label derived from type string)

### Adding a new relationship type

1. Add the type string to `RELATIONSHIP_TYPES` in `base.py`
2. Update PROMPT-002 in `relation_extractor.py`
3. Update `PROMPTS.md` PROMPT-002 relationship types list
4. Update `SCHEMA.md` Relationship Types section

---

## Error Handling

- Claude API errors → re-raised (caller handles retry/abort)
- JSON parse failures → logged as WARNING, chunk skipped, extraction continues
- Unknown entity/relationship types in Claude response → accepted (not filtered out)
