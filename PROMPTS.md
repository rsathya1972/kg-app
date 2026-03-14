# Ontology Graph Studio — Claude Prompt Catalog

> This file catalogs every AI prompt in the codebase: purpose, model, token budget, input/output contract, and location.
> Update this file whenever a prompt is added, changed, or removed.

---

## Conventions

- **Model abbreviations**: H = `claude-haiku-4-5-20251001`, S = `claude-sonnet-4-6`
- **All prompts** must include a "NEVER fabricate" instruction
- **All prompts** must instruct Claude to return "ONLY valid JSON, no markdown fences"
- Strip markdown fences before `json.loads()` — use `json_utils.strip_fences()`
- Haiku for extraction/classification (fast, cheap); Sonnet for generation/reasoning (quality)

---

## Live Prompts

### PROMPT-001 — Entity Extraction

| Field | Value |
|-------|-------|
| **File** | `backend/app/extraction/entity_extractor.py` lines 18–44 |
| **Model** | Haiku (H) |
| **Max tokens** | 2048 |
| **Called by** | `EntityExtractionAgent.extract(text, chunk_index)` |
| **Trigger** | Once per text chunk (SlidingWindowChunker, 600 tokens, 50 overlap) |

**Input contract**

```
{document text chunk — ≤600 tokens}
```

**System prompt**

```
Extract all named entities from the following text.
Return ONLY valid JSON — no markdown fences, no commentary.

Schema:
{
  "entities": [
    {
      "name": "string",
      "type": "string",
      "attributes": {},
      "evidence": "verbatim excerpt ≤200 chars",
      "confidence": 0.0–1.0
    }
  ]
}

Rules:
- NEVER fabricate entities not present in the text
- Valid types: Company, Person, Product, Contract, Location, Technology, Policy, Regulation
- evidence must be a verbatim excerpt from the input, ≤200 characters
- confidence reflects extraction certainty (0.0–1.0)
```

**Output contract**

```json
{
  "entities": [
    { "name": "AWS", "type": "Technology", "attributes": {}, "evidence": "hosted on AWS", "confidence": 0.95 }
  ]
}
```

**Post-processing**
- JSON parse failures: logged as WARNING, chunk skipped
- Deduplication: highest-confidence instance kept per entity name

---

### PROMPT-002 — Relationship Extraction

| Field | Value |
|-------|-------|
| **File** | `backend/app/extraction/relation_extractor.py` lines 26–56 |
| **Model** | Haiku (H) |
| **Max tokens** | 2048 |
| **Called by** | `RelationExtractor.extract(text, entities, chunk_index)` |
| **Trigger** | Once per chunk that contains ≥2 entity names |

**Input contract**

```
Entities present in this chunk: [name1, name2, ...]
{document text chunk — ≤600 tokens}
```

**System prompt**

```
Identify relationships between the named entities listed below.
Return ONLY valid JSON — no markdown fences.

Schema:
{
  "relations": [
    {
      "source": "entity name",
      "type": "relationship type",
      "target": "entity name",
      "evidence": "verbatim excerpt ≤200 chars",
      "confidence": 0.0–1.0
    }
  ]
}

Rules:
- NEVER fabricate relationships not supported by the text
- source and target MUST exactly match names from the provided entity list
- Valid types: WORKS_FOR, OWNS, USES, BELONGS_TO, RENEWS, EXPIRES_ON, LOCATED_IN, DEPENDS_ON, SELLS_TO, GOVERNED_BY
- evidence must be a verbatim excerpt from the input, ≤200 characters
```

**Output contract**

```json
{
  "relations": [
    { "source": "Acme Corp", "type": "USES", "target": "AWS", "evidence": "Acme's infrastructure runs on AWS", "confidence": 0.9 }
  ]
}
```

**Post-processing**
- Deduplication: highest-confidence kept per (source, type, target) triple

---

### PROMPT-003 — NL → Cypher Query Translation

| Field | Value |
|-------|-------|
| **File** | `backend/app/agents/query_agent.py` lines 13–22 |
| **Model** | Haiku (H) |
| **Max tokens** | 512 |
| **Called by** | `QueryPlanningAgent.plan_and_execute(query, schema_hint)` |
| **Trigger** | On every `POST /api/query` request |

**System prompt**

```
You are a Cypher query expert for Neo4j knowledge graphs.

Graph schema:
- All entity nodes have: pg_id (UUID), name (string), entity_type (string), confidence (float), document_id (string)
- Entity labels are PascalCase: Company, Person, Technology, Contract, Location, Product, Policy, Regulation
- All relationships have type RELATES with property type (WORKS_FOR, OWNS, USES, BELONGS_TO, RENEWS, EXPIRES_ON, LOCATED_IN, DEPENDS_ON, SELLS_TO, GOVERNED_BY)

Return ONLY valid Cypher. No markdown. No explanation.
```

**Input contract**

```
{natural language question string}
Optional schema hint: {domain context string}
```

**Output contract**

```cypher
MATCH (c:Company)-[r:RELATES {type: 'USES'}]->(t:Technology)
WHERE t.name = 'AWS'
RETURN c.name, r.confidence
LIMIT 25
```

**Post-processing**
- Strip markdown backtick fences (` ```cypher ... ``` `) before execution
- Execute via `neo4j_client.run(cypher)`

---

### PROMPT-004 — GraphRAG Answer Generation

| Field | Value |
|-------|-------|
| **File** | `backend/app/agents/rag_agent.py` lines 15–19 |
| **Model** | Sonnet (S) — `claude-sonnet-4-6` |
| **Max tokens** | 1024 |
| **Called by** | `GraphRAGAgent.answer(question, db, top_k)` |
| **Trigger** | On every `POST /api/query` request after semantic search |

**System prompt**

```
You are a helpful assistant that answers questions using ONLY the provided document context.
Be concise, factual, and cite source documents.
If the context does not contain enough information to answer, say so clearly.
NEVER fabricate facts not present in the context.
```

**Input contract**

```
Context from {N} document chunks:
[Chunk 1 — {filename}, score {similarity}]
{chunk text}

[Chunk 2 — ...]
...

Question: {user question}
```

**Output contract**

Free-form natural language answer citing sources. Not JSON.

**Notes**
- Uses Sonnet (not Haiku) — quality matters more than speed for answer synthesis
- Context built from top-K semantic search results (`embedding_service.semantic_search`)
- Sources array returned alongside answer for frontend citation display

---

## Stub Prompts (Not Yet Wired)

### PROMPT-005 — Entity → Ontology Alignment *(stub)*

| Field | Value |
|-------|-------|
| **File** | `backend/app/ontology/aligner.py` lines 11–24 |
| **Model** | Sonnet (S) — planned |
| **Status** | `NotImplementedError` — planned for Step 4 |

**Intended system prompt**

```
Map each entity to the most appropriate ontology class.
Return ONLY valid JSON:
{
  "alignments": [
    { "entity_text": "string", "ontology_class": "string", "confidence": 0.0–1.0 }
  ]
}
NEVER assign a class not in the provided available_classes list.
```

**When implemented**: feed extracted entities + `ontology_manager.list_classes()` into this prompt; store alignment in `ExtractedEntity.attributes_json["ontology_class"]`.

---

### PROMPT-006 — NL → StructuredQuery Parsing *(stub)*

| Field | Value |
|-------|-------|
| **File** | `backend/app/query/nl_parser.py` lines 10–21 |
| **Model** | Sonnet (S) — planned |
| **Status** | `NotImplementedError` — planned for Step 7 |

**Intended system prompt**

```
Parse the following natural language query into a structured graph query.
Return ONLY valid JSON:
{
  "intent": "find|count|relate|path",
  "entity_types": ["string"],
  "filters": {},
  "relations": ["string"],
  "limit": integer
}
```

**When implemented**: replaces the ad-hoc Cypher generation in PROMPT-003 with a two-step pipeline: NL → StructuredQuery → CypherBuilder.

---

## OpenAI Calls

### EMBED-001 — Document Chunk Embedding

| Field | Value |
|-------|-------|
| **File** | `backend/app/vector_memory/embedding_service.py` |
| **Model** | `text-embedding-3-small` (OpenAI) |
| **Dimensions** | 1536 |
| **Called by** | `VectorEmbeddingService.embed_document(document_id, db)` |
| **Trigger** | After file ingestion; called via `POST /api/vector/embed` |

**Input**: text chunks from `SlidingWindowChunker`
**Output**: `vector(1536)` stored in `chunk_embeddings.embedding`
**Notes**: Input truncated to 32k chars before embedding to respect model limits.

---

### EMBED-002 — Query Embedding (Semantic Search)

| Field | Value |
|-------|-------|
| **File** | `backend/app/vector_memory/embedding_service.py` |
| **Model** | `text-embedding-3-small` (OpenAI) |
| **Called by** | `VectorEmbeddingService.semantic_search(query, top_k, db)` |
| **Trigger** | On every search request |

**Input**: user query string
**Output**: `vector(1536)` used for pgvector cosine similarity search against `chunk_embeddings`

---

## Adding a New Prompt

1. Write the prompt in the relevant module file
2. Add an entry to this catalog above following the existing format
3. Assign the next PROMPT-NNN id
4. Specify model, max_tokens, calling function, trigger condition
5. Document the exact input/output contract
6. Update `ROADMAP.md` if this wires up a previously stubbed step
