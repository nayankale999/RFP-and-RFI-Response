import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    client_name: str | None = None
    industry: str | None = None
    deadline: datetime | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    client_name: str | None = None
    industry: str | None = None
    status: str | None = None
    deadline: datetime | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
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

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
