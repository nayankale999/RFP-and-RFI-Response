import uuid
from datetime import datetime

from pydantic import BaseModel


class ExportRequest(BaseModel):
    template_id: uuid.UUID | None = None
    include_sections: list[str] | None = None
    company_name: str = "Company Name"
    company_description: str | None = None


class ExportStatus(BaseModel):
    project_id: uuid.UUID
    status: str  # pending, generating, completed, failed
    download_url: str | None = None
    error_message: str | None = None


class KnowledgeBaseCreate(BaseModel):
    title: str
    content: str
    category: str | None = None
    tags: list[str] | None = None


class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    category: str | None
    tags: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseSearchResult(BaseModel):
    entries: list[KnowledgeBaseResponse]
    total: int
