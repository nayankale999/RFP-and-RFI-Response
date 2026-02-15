import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int | None
    doc_category: str | None
    page_count: int | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentParseStatus(BaseModel):
    id: uuid.UUID
    status: str
    doc_category: str | None
    page_count: int | None
    error_message: str | None
