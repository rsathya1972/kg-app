from pydantic import BaseModel


class ValidationRequest(BaseModel):
    document_id: str | None = None   # None = validate entire graph
    rule_set: str = "default"        # named rule set to apply


class ValidationViolation(BaseModel):
    rule_id: str
    severity: str          # "error" | "warning" | "info"
    message: str
    node_id: str | None = None
    property_name: str | None = None


class ValidationReportResponse(BaseModel):
    document_id: str | None
    rule_set: str
    total_checked: int
    violations: list[ValidationViolation]
    error_count: int
    warning_count: int
    passed: bool
