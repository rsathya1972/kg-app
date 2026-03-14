# Ontology Module

Manages the domain ontology: classes, properties, and entity-to-class alignment.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | `OntologyClass`, `OntologyProperty` dataclasses |
| `manager.py` | `OntologyManager` singleton — in-memory CRUD |
| `aligner.py` | Stub — entity → ontology class alignment via Claude Sonnet |

---

## Current Status

The ontology manager is **fully functional but in-memory only** (Step 4). Data does not persist across restarts. Persistence to `ontology_versions` PostgreSQL table is planned.

---

## Key Class

### `OntologyManager`

Singleton available at `app.ontology.manager.ontology_manager`.

```python
from app.ontology.manager import ontology_manager

# List all classes
classes: list[OntologyClass] = ontology_manager.list_classes()

# Create a class
cls = ontology_manager.create_class(
    name="SoftwareProduct",
    description="A commercial software product",
    parent_class="Product"  # optional
)

# Get by name
cls = ontology_manager.get_class_by_name("Company")

# Delete
ontology_manager.delete_class(cls.id)
```

### Default Classes (seeded on init)

1. `Entity` — base class for all entities
2. `Person` — a human individual
3. `Organization` — a company, government body, or institution
4. `Location` — a physical or geographic place
5. `Concept` — an abstract idea or category

---

## Planned: Entity Alignment (`aligner.py`)

When implemented (Step 4), `EntityAligner.align(entities, db)` will:
1. Load current ontology classes from `ontology_manager.list_classes()`
2. Send entities + class list to Claude Sonnet (PROMPT-005)
3. Return `{entity_id → ontology_class_name}` mapping
4. Store alignment in `ExtractedEntity.attributes_json["ontology_class"]`

Current state: `NotImplementedError`.

---

## How to Extend the Ontology

### Add a new class via API

```bash
curl -X POST http://localhost:8000/api/ontology/classes \
  -H "Content-Type: application/json" \
  -d '{"name": "Contract", "description": "A legal agreement", "parent_class": "Entity"}'
```

### Add a new class programmatically

```python
ontology_manager.create_class(
    name="Contract",
    description="A legal agreement between parties",
    parent_class="Entity"
)
```

---

## Persistence Migration (Step 4)

When persistence is implemented:
1. `create_class()` will write to `ontology_versions` table
2. Each change creates a new version snapshot (audit trail)
3. `list_classes()` will query the latest version from PostgreSQL
4. In-memory cache used for fast repeated reads
