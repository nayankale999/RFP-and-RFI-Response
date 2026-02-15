import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    upload_context: str | None = None
    client_name: str | None = None
    industry: str | None = None
    deadline: datetime | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    upload_context: str | None = None
    client_name: str | None = None
    industry: str | None = None
    status: str | None = None
    deadline: datetime | None = None
    processing_status: str | None = None
    processing_message: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    upload_context: str | None = None
    status: str
    client_name: str | None
    industry: str | None
    deadline: datetime | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    requirement_count: int = 0
    response_count: int = 0
    processing_status: str | None = None
    processing_message: str | None = None
    processing_started_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
