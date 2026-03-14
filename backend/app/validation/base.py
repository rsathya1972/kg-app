"""
Validation dataclasses: ValidationRule and ValidationReport.
"""
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationRule:
    """A single validation rule applied to the graph."""
    id: str
    name: str
    description: str
    severity: Severity = Severity.WARNING


@dataclass
class ValidationViolation:
    """A single rule violation."""
    rule_id: str
    severity: Severity
    message: str
    node_id: str | None = None
    property_name: str | None = None


@dataclass
class ValidationReport:
    """Aggregated result of a validation run."""
    document_id: str | None
    rule_set: str
    total_checked: int
    violations: list[ValidationViolation] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)

    @property
    def passed(self) -> bool:
        return self.error_count == 0
