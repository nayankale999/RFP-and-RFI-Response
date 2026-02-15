import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ResponseOut(BaseModel):
    id: uuid.UUID
    requirement_id: uuid.UUID
    project_id: uuid.UUID
    compliance_status: str
    response_text: str
    confidence_score: float | None
    source_refs: dict | None
    is_ai_generated: bool
    is_reviewed: bool
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResponseUpdate(BaseModel):
    compliance_status: str | None = None
    response_text: str | None = None
    notes: str | None = None
    is_reviewed: bool | None = None


class ResponseListOut(BaseModel):
    responses: list[ResponseOut]
    total: int
    compliance_scores: dict = {}


class ComplianceScoresOut(BaseModel):
    overall_score: float
    functional_score: float
    non_functional_score: float
    commercial_score: float = 0
    technical_score: float = 0
    scores_by_type: dict[str, float] = {}
    total_requirements: int
    total_responses: int
    status_breakdown: dict[str, int] = {}
