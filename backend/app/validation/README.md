# Validation Module

Validates the knowledge graph against user-defined rules and detects consistency issues.

**Status**: Stub — planned for Step 8.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | `Severity`, `ValidationRule`, `ValidationViolation`, `ValidationReport` types |
| `shacl_validator.py` | Stub — SHACL-style constraint validation |
| `consistency_checker.py` | Stub — orphan nodes, duplicates, contradictions |

---

## Type Definitions

### `Severity`

```python
class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
```

### `ValidationRule`

```python
@dataclass
class ValidationRule:
    id: str
    name: str
    description: str
    severity: Severity
```

### `ValidationReport`

```python
@dataclass
class ValidationReport:
    document_id: str
    rule_set: str
    total_checked: int
    violations: list[ValidationViolation]

    @property
    def error_count(self) -> int: ...
    @property
    def warning_count(self) -> int: ...
    @property
    def passed(self) -> bool: ...  # True if no ERROR violations
```

---

## Planned Rules (Step 8)

### SHACL-style constraints

| Rule ID | Description | Severity |
|---------|-------------|----------|
| `sh:minCount` | Required properties present on entity | ERROR |
| `sh:datatype` | Property values match expected type | ERROR |
| `sh:class` | Relationship target is correct ontology class | WARNING |
| `sh:pattern` | String property matches regex pattern | WARNING |

### Consistency checks

| Check | Description | Severity |
|-------|-------------|----------|
| `orphan_node` | Entity exists with zero relationships | INFO |
| `duplicate_entity` | Same name + type appears multiple times | WARNING |
| `contradicting_relation` | A → B and B → A via same relationship type | WARNING |
| `low_confidence_cluster` | Subgraph where all edges < 0.4 confidence | INFO |

---

## How to Implement (Step 8)

1. Implement `ShaclValidator.validate(document_id, rules, db)` in `shacl_validator.py`
2. Implement `ConsistencyChecker.check(document_id, db)` in `consistency_checker.py`
3. Wire both into `POST /api/validation/run` route in `api/routes/validation.py`
4. Store results in a new `validation_reports` PostgreSQL table
5. Return `ValidationReport` via API
6. Build Validation page in frontend (`/validation`)
