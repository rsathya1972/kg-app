from datetime import datetime

from pydantic import BaseModel


class StepResult(BaseModel):
    step_name: str
    status: str  # "pending" | "running" | "completed" | "failed" | "skipped"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    output_summary: str | None = None
    error: str | None = None


class AgentDecision(BaseModel):
    agent: str
    message: str
    timestamp: datetime


class AgentRunSummary(BaseModel):
    id: str
    document_id: str | None
    document_name: str | None
    status: str
    current_step: str | None
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    steps_count: int
    completed_steps_count: int


class AgentRunDetail(AgentRunSummary):
    steps: list[StepResult]
    decisions: list[AgentDecision]


class AgentRunListResponse(BaseModel):
    runs: list[AgentRunSummary]
    total: int


class TriggerRunRequest(BaseModel):
    domain_hint: str | None = None


class TriggerRunResponse(BaseModel):
    run_id: str
    status: str


class QueryRequest(BaseModel):
    query: str
    document_id: str | None = None


class QueryResponse(BaseModel):
    query: str
    cypher: str | None = None
    results: list[dict]
    answer: str | None = None
    sources: list[dict] = []
    error: str | None = None
