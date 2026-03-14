"""
Validation reporter: formats ValidationReport into API response dicts.
"""
from app.validation.base import ValidationReport


class ValidationReporter:
    """Formats validation reports for API responses."""

    def to_dict(self, report: ValidationReport) -> dict:
        """Convert a ValidationReport to a serializable dict."""
        return {
            "document_id": report.document_id,
            "rule_set": report.rule_set,
            "total_checked": report.total_checked,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "passed": report.passed,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity.value,
                    "message": v.message,
                    "node_id": v.node_id,
                    "property_name": v.property_name,
                }
                for v in report.violations
            ],
        }

    def summary(self, report: ValidationReport) -> str:
        """Return a one-line human-readable summary."""
        status = "PASSED" if report.passed else "FAILED"
        return (
            f"Validation {status}: {report.error_count} errors, "
            f"{report.warning_count} warnings across {report.total_checked} items"
        )
