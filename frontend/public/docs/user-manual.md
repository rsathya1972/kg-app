# Ontology Graph Studio — User Manual

**Version 1.0 | Internal Enterprise Platform**

---

## 1. Product Overview

Ontology Graph Studio is an AI-powered knowledge graph platform that transforms unstructured documents into a structured, queryable knowledge graph. The system automatically extracts entities (companies, people, products, contracts, technologies) and the relationships between them, organises them according to a domain ontology, and stores the resulting graph in a dedicated graph database.

### Problems It Solves

| Problem | How the Platform Helps |
|---------|------------------------|
| Knowledge locked in documents | Extracts structured entities and relationships automatically |
| No visibility into how entities are connected | Builds a traversable knowledge graph with relationship types |
| Inconsistent terminology across documents | Ontology layer normalises entity types and relationships |
| Slow, manual research across large document sets | Natural language queries and semantic search surface answers instantly |
| No feedback on data quality | Knowledge Health Dashboard monitors accuracy, coverage, and consistency |

### Primary Use Cases

- **Contract and vendor analysis** — Understand which companies supply what, when contracts expire, and how vendor relationships are structured
- **Technology stack mapping** — Map which services depend on which platforms, find undocumented dependencies
- **Regulatory and compliance intelligence** — Surface which policies govern which entities, identify gaps in governance coverage
- **Research and discovery** — Ask natural language questions that draw on both structured graph data and raw document passages

---

## 2. Platform Overview

Ontology Graph Studio processes documents through a five-stage AI pipeline and surfaces the results across eleven specialised modules.

```
Documents → Extract Entities → Extract Relationships → Build Ontology → Write Graph → Embed for Search
                                                                                         ↓
                                                        Query · Copilot · Health Dashboard · Semantic Search
```

### What the Platform Produces

After processing a document, the platform maintains:

- **Entities** — Named objects (Company, Person, Product, Contract, Location, Technology, Policy, Regulation) with confidence scores and source evidence
- **Relationships** — Typed connections between entities (OWNS, USES, DEPENDS_ON, EXPIRES_ON, GOVERNED_BY, etc.)
- **Ontology** — The vocabulary of entity types and relationship predicates discovered for your domain
- **Knowledge Graph** — A traversable graph in Neo4j where entities are nodes and relationships are edges
- **Vector Index** — Semantic embeddings of document chunks enabling similarity-based retrieval
- **Health Metrics** — Ongoing quality assessment of graph accuracy, coverage, and consistency

---

## 3. High-Level Architecture

The following diagram shows how the platform components interact:

```mermaid
graph TB
    User([Business User]) --> FE["Next.js Frontend\n(port 3000)"]
    FE --> API["FastAPI Backend\n(port 8000)"]

    API --> CLAUDE["Anthropic Claude\nHaiku — extraction\nSonnet — reasoning"]
    API --> OPENAI["OpenAI\nText Embeddings"]

    API --> PG[("PostgreSQL 16\nDocuments · Entities\nRelationships · Ontology\nEmbeddings (pgvector)")]
    API --> NEO[("Neo4j Graph DB\nNodes · Edges\nbolt://localhost:7687")]

    subgraph AI Pipeline
        ENT["Entity Extractor"] --> REL["Relationship Extractor"]
        REL --> ONT["Ontology Builder"]
        ONT --> GW["Graph Writer"]
        GW --> VEC["Vector Embedder"]
    end

    API --> AI Pipeline
```

### Components at a Glance

| Component | Role |
|-----------|------|
| **Next.js Frontend** | User interface — 11 modules accessible from left navigation |
| **FastAPI Backend** | REST API server — orchestrates AI pipeline, database access, and business logic |
| **PostgreSQL + pgvector** | Stores documents, extracted entities, relationships, ontology versions, and vector embeddings |
| **Neo4j** | Stores the knowledge graph (nodes = entities, edges = relationships) for traversal queries |
| **Anthropic Claude Haiku** | Fast AI model — entity extraction, relationship extraction, ontology class identification |
| **Anthropic Claude Sonnet** | High-quality AI model — ontology discovery, GraphRAG answer synthesis |
| **OpenAI Embeddings** | Converts document chunks into vectors for semantic similarity search |

---

## 4. System Navigation

The application uses a fixed left-hand navigation panel with eleven modules. The active module is highlighted.

```
┌─────────────────┐
│  Ontology Graph │
│     Studio      │
├─────────────────┤
│ 🏠 Home         │
│ ⬆ Upload Docs  │
│ ⚙ Extract       │
│ 🌿 Ontology     │
│ 🌐 Graph Viewer │
│ 🔍 Query        │
│ 🧠 Copilot      │
│ ❤ Health        │
│ ✓ Validation    │
│ ✦ Semantic Srch │
│ 🤖 Agent Monitor│
│ ❓ Help & Docs  │
└─────────────────┘
```

### Navigation Tips

- The **Home** page shows live backend health status — check here first if the app seems unresponsive
- The typical workflow follows the navigation order: Upload → Extract → Ontology → Graph → Query/Copilot
- **Agent Monitor** can run the entire pipeline in one click instead of running each step manually
- **Knowledge Health** is used periodically to assess and improve graph quality

---

## 5. Module Guide

### 5.1 Upload Documents

The Upload module ingests raw documents into the platform. Supported formats are TXT, PDF, and DOCX. The platform reads the raw text, detects the language, counts words, and stores the document for downstream processing.

**Key capabilities:**
- Upload files via drag-and-drop or file picker
- Paste raw text directly
- View all previously ingested documents with metadata (size, word count, language, date)
- Delete documents (cascades to all extracted data)

**When to use:** Start here with every new document before running any extraction.

---

### 5.2 Extract Entities

The Extract module runs AI-powered Named Entity Recognition (NER) on an ingested document and then identifies the relationships between those entities.

**Entities tab:**
- Select a document and click **Run Extraction**
- Claude Haiku reads the document in overlapping chunks and identifies entities of these types: `Company`, `Person`, `Product`, `Contract`, `Location`, `Technology`, `Policy`, `Regulation`
- Each entity has a **confidence score** (0–100%) indicating how certain the model is
- Filter entities by type using the pill filters
- Click any entity row to see the full source evidence text

**Relationships tab:**
- After entities exist, click **Run Relationship Extraction**
- The model reads entity pairs in context and identifies typed relationships: `WORKS_FOR`, `OWNS`, `USES`, `BELONGS_TO`, `RENEWS`, `EXPIRES_ON`, `LOCATED_IN`, `DEPENDS_ON`, `SELLS_TO`, `GOVERNED_BY`
- A **network graph** visualises all entities as nodes and relationships as labelled edges
- Click any relationship row for evidence and confidence details

**When to use:** After uploading a document. Run entity extraction first, then relationship extraction.

---

### 5.3 Ontology Builder

The Ontology module discovers the domain-specific vocabulary that best describes your document corpus and maintains versioned ontology snapshots.

**What it does:**
- Analyses extracted entities and relationships to infer a domain ontology
- Proposes class names, descriptions, properties, and synonyms for each entity type
- Identifies relationship predicates and the source/target class pairs they connect
- Stores each generation as a numbered version for comparison

**Ontology Explorer has three tabs:**
- **Classes** — View each discovered entity class with its properties, description, and synonyms
- **Relationships** — View the full relationship vocabulary with source → predicate → target structure
- **JSON** — Export the raw ontology structure for use in external tools

**Domain hints:** Use the quick-select pills (telecom, saas, insurance, healthcare, finance) or type a custom hint to guide the model toward the right vocabulary.

**When to use:** After extracting entities from several documents. Generate the ontology to understand your domain vocabulary before querying.

---

### 5.4 Graph Viewer

The Graph Viewer provides an interactive visual explorer of the Neo4j knowledge graph.

**Key capabilities:**
- Select a document and click **Build Graph** to write extracted entities and relationships into Neo4j
- View a live force-layout graph with colour-coded nodes per entity type
- Toggle entity type filters to show/hide categories of nodes
- Click any node to open a detail panel showing name, type, confidence, and attributes
- Pan, zoom, and drag nodes to explore the graph structure

**Node colours:**
| Colour | Entity Type |
|--------|------------|
| Blue | Company / Organization |
| Green | Person |
| Purple | Technology |
| Orange | Product |
| Red | Location |
| Cyan | Event |
| Amber | Concept |
| Violet | Service |

**When to use:** After running the AI pipeline on a document. Use Graph Viewer to visually confirm that relationships are being captured correctly.

---

### 5.5 Knowledge Copilot

Knowledge Copilot is a conversational interface that answers natural language questions by combining three retrieval sources: ontology reasoning, graph traversal, and semantic document search.

**How a query works:**
1. Your question is matched against ontology class names to identify relevant entity types
2. The knowledge graph is traversed for matching nodes and their relationships
3. Semantically similar document passages are retrieved
4. Claude Sonnet synthesises a grounded answer from all three sources

**The interface shows:**
- **Synthesised answer** — A direct response grounded in your data
- **Reasoning trace** — Step-by-step explanation of what the model did at each pipeline stage
- **Graph nodes** — The entities retrieved from Neo4j
- **Relationships** — The edges traversed during graph traversal
- **Document chunks** — The raw passages from your documents that supported the answer

**Example questions:**
- "Which companies depend on AWS?"
- "Which contracts expire next quarter?"
- "Which customers use product X?"
- "What technologies are used by the engineering team?"

**When to use:** For research questions that require connecting entities across multiple documents. More powerful than keyword search — it understands relationships.

---

### 5.6 Knowledge Health Dashboard

The Knowledge Health Dashboard gives you continuous visibility into graph quality and drives ontology evolution through AI-generated improvement proposals.

**Four tabs:**

**Metrics** — Key quality indicators:
- Entity Accuracy (% of entities above confidence threshold)
- Relationship Accuracy
- Ontology Coverage (% of entity types matched to the active ontology)
- Graph Completeness (average relationships per entity)
- Total entity, relationship, and graph counts

**Issues** — Detected quality problems, filterable by type and severity:
- `duplicate_entity` (error) — Same entity appears multiple times in one document
- `low_confidence_entity` (warning) — Entity with confidence below threshold
- `unknown_entity_type` (warning) — Entity type not in the active ontology
- `orphan_entity` (info) — Entity with no relationships
- `sparse_relationships` (info) — Document with many entities but few relationships

**Proposals** — AI-generated ontology improvement suggestions:
- `add_class` — New entity type discovered in data, not yet in ontology
- `merge_class` — Two types likely represent the same concept
- `rename_class` — A type name is inconsistent with convention
- Click **Apply** to immediately add the class to your active ontology

**Heatmap** — Confidence distribution by entity type, with a list of the lowest-confidence individual entities

**When to use:** Periodically after ingesting new documents. Run Analysis to refresh all metrics and proposals.

---

### 5.7 Semantic Search

Semantic Search finds document passages that are conceptually similar to your query, even if they don't share exact keywords.

**How it works:**
- Your query is converted to a vector embedding
- The platform retrieves the top-K document chunks with highest cosine similarity
- Results are ranked by similarity score and shown with source filename and chunk context

**Similarity score guide:**
- **≥ 80%** — Strong match (green badge)
- **≥ 60%** — Moderate match (amber badge)
- **< 60%** — Weak match (grey badge)

**When to use:** When you know what you're looking for but want to find all relevant passages across documents, including paraphrased or differently-worded versions.

---

### 5.8 Agent Monitor

Agent Monitor orchestrates the full five-stage AI pipeline in a single click and provides real-time progress tracking.

**Pipeline stages (run in sequence):**
1. **Entity Extraction** — Identifies all entities in the document
2. **Relationship Discovery** — Finds relationships between extracted entities
3. **Ontology Builder** — Updates domain ontology based on new data
4. **Graph Update** — Writes entities and relationships to Neo4j
5. **Vector Memory** — Embeds document chunks into the vector index

**The monitor shows:**
- **Timeline tab** — Step-by-step progress with durations and output summaries
- **Task Graph tab** — DAG visualisation of pipeline stages, colour-coded by status (green = done, blue = running, red = failed)
- **Decisions tab** — Agent reasoning events logged during execution

**Real-time updates:** The monitor streams live events via SSE (Server-Sent Events) — the timeline updates as each stage completes.

**When to use:** When you want to run the entire pipeline in one step rather than executing each module individually.

---

### 5.9 Validation *(Planned)*

SHACL/OWL-RL constraint checking against the active ontology. Will detect entities with missing required properties, invalid relationship targets, and ontology violations.

### 5.10 Query *(Planned)*

A full-featured query interface supporting natural language-to-Cypher translation and direct Cypher/SPARQL query execution against the knowledge graph.

---

## 6. Step-by-Step Workflows

### 6.1 Ingesting a Document

1. Click **Upload Documents** in the left navigation
2. Drag your file (TXT, PDF, or DOCX) onto the upload area, or click to browse
3. Wait for the green confirmation — the document now appears in the document list
4. Note the document ID for use in downstream steps

---

### 6.2 Running the Full AI Pipeline (Recommended)

The fastest path from document to knowledge graph:

1. Click **Agent Monitor** in the left navigation
2. Select your document from the dropdown
3. (Optional) Enter a **domain hint** — e.g., `finance`, `healthcare`, `telecom` — to guide ontology generation
4. Click **Run Pipeline**
5. Watch the timeline update in real-time as each stage completes
6. When status shows **Completed**, all five stages are done

The pipeline completes entity extraction, relationship discovery, ontology generation, graph writing, and vector embedding in one sequence.

---

### 6.3 Exploring the Knowledge Graph

After running the pipeline:

1. Click **Graph Viewer**
2. Select your document from the dropdown
3. If the graph is empty, click **Build Graph** (this writes to Neo4j)
4. The graph renders automatically — drag nodes, zoom, and pan to explore
5. Use the entity type filter pills to focus on a subset (e.g., show only Technology and Company nodes)
6. Click any node to open the detail panel — view name, type, confidence, and attributes

---

### 6.4 Asking Questions with Knowledge Copilot

1. Click **Knowledge Copilot**
2. Click an example question or type your own in the text area
3. Press **Enter** (or click Send)
4. Wait for the four-stage retrieval to complete
5. Read the synthesised answer at the top
6. Expand the **Reasoning Trace** to see which graph nodes and passages were used
7. Scroll down to review individual graph nodes, relationships, and document chunks

---

### 6.5 Running a Knowledge Health Analysis

1. Click **Knowledge Health**
2. On the Metrics tab, review the current quality indicators
3. Click **Run Analysis** (top-right button)
4. Optional: enable **Auto-correct** to remove duplicates and normalise entity types automatically
5. After analysis completes, the banner shows: issues detected, proposals generated, corrections applied
6. Switch to the **Issues tab** — filter by severity (`error`, `warning`, `info`) to prioritise work
7. Switch to the **Proposals tab** — review AI-generated ontology improvement suggestions
8. Click **Apply** on proposals you agree with — this immediately adds the class to your ontology
9. Click **Dismiss** to discard proposals that are not appropriate for your domain
10. Switch to the **Heatmap tab** to see which entity types have the lowest average confidence

---

### 6.6 Semantic Search

1. Click **Semantic Search**
2. Type your query in the search box (e.g., "payment terms and late fees")
3. Adjust the **Top K** dropdown to control how many results to return (default: 5)
4. Press **Enter** or click **Search**
5. Review results ranked by similarity score — click any result to expand the full passage

---

## 7. Practical Examples

### Example 1: Analysing a Contract Portfolio

**Scenario:** A legal operations team has uploaded 20 vendor contracts and wants to know which ones expire in the next 90 days and which vendors supply overlapping services.

**Goal:** Find contracts expiring soon and map vendor relationships.

**Steps:**
1. Upload all contract PDF files via the **Upload Documents** module
2. For each document, run the full pipeline via **Agent Monitor** with domain hint `contracts`
3. Open **Knowledge Copilot** and ask: *"Which contracts expire in the next quarter?"*
4. Review the synthesised answer and the supporting document chunks
5. Open **Graph Viewer** and filter to show only `Contract` and `Company` nodes — visually inspect vendor relationships
6. Open **Knowledge Health** and run analysis — check Issues tab for `duplicate_entity` errors (same vendor appearing under different names)
7. Apply any `merge_class` or `rename_class` proposals to normalise vendor entity types

**Expected Result:** A list of expiring contracts with supporting evidence, a visual vendor relationship graph, and a cleaner ontology with normalised vendor terminology.

---

### Example 2: Mapping a Technology Stack

**Scenario:** An infrastructure team has uploaded engineering documentation, runbooks, and architecture notes, and wants to understand which services depend on which platforms.

**Goal:** Map service dependencies and identify undocumented relationships.

**Steps:**
1. Upload all technical documents via **Upload Documents**
2. Run the full pipeline via **Agent Monitor** with domain hint `technology infrastructure`
3. Open **Graph Viewer** and filter to `Technology` nodes only — inspect dependency edges
4. Open **Knowledge Copilot** and ask: *"Which services depend on AWS?"* and *"What databases does the platform use?"*
5. Open **Ontology Builder** — review the discovered ontology classes; check whether `Platform`, `Service`, and `Technology` are correctly separated
6. Open **Knowledge Health** → Issues tab — look for `unknown_entity_type` issues (e.g., if `k8s` is not linked to `Kubernetes`)
7. Apply `add_class` or `rename_class` proposals to consolidate entity types

**Expected Result:** A fully mapped dependency graph, identified gaps in documentation, and a normalised ontology for the infrastructure domain.

---

### Example 3: Identifying Low-Confidence Knowledge

**Scenario:** A data governance team wants to audit the reliability of extracted knowledge before publishing the graph to downstream consumers.

**Goal:** Find and remediate low-confidence entities and relationships.

**Steps:**
1. Open **Knowledge Health** → **Metrics tab**
2. Review Entity Accuracy and Relationship Accuracy scores
3. Click **Run Analysis** with confidence threshold set to `0.7`
4. Open the **Issues tab** — filter by severity `warning` — review `low_confidence_entity` entries
5. For each flagged entity, note the source `document_id`
6. Open **Extract Entities** → select the source document → find the entity in the table
7. Review the evidence text — is the extraction plausible given the source text?
8. Open the **Heatmap tab** — identify which entity types have the lowest average confidence
9. Consider whether the document requires re-ingestion or manual curation

**Expected Result:** A prioritised list of knowledge quality issues with source evidence, enabling targeted remediation.

---

### Example 4: Asking Multi-Hop Questions

**Scenario:** A risk analyst wants to understand whether any of the company's technology vendors are subject to the same regulatory framework, creating a concentration risk.

**Goal:** Trace entity relationships across two or more hops.

**Steps:**
1. Ensure vendor contracts and regulatory documents have been uploaded and processed
2. Open **Knowledge Copilot** and ask: *"Which technology vendors are governed by GDPR?"*
3. Expand the **Reasoning Trace** — verify that the graph traversal found `Technology → GOVERNED_BY → Regulation` paths
4. Review the **Graph Nodes** panel — confirm which vendors appeared and which regulation nodes were linked
5. Ask follow-up: *"Which of those vendors are also used by the engineering platform?"*
6. Use **Graph Viewer** to visually trace the multi-hop path: Company → USES → Technology → GOVERNED_BY → Regulation

**Expected Result:** A clear answer connecting vendors to regulatory frameworks through the graph, with full source evidence from the original documents.
