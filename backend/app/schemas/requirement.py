import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RequirementResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    document_id: uuid.UUID | None
    req_number: str
    title: str
    description: str
    type: str
    category: str | None
    is_mandatory: bool
    reference_page: int | None
    reference_section: str | None
    response_required: bool
    priority: str
    confidence_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RequirementUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: str | None = None
    category: str | None = None
    is_mandatory: bool | None = None
    response_required: bool | None = None
    priority: str | None = None


class RequirementListResponse(BaseModel):
    requirements: list[RequirementResponse]
    total: int
    type_counts: dict[str, int] = {}
