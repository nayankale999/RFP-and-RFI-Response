import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.document import Document
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentParseStatus
from app.documents.parsers.factory import get_parser_factory
from app.shared.storage import get_storage_client
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/projects/{project_id}/documents", response_model=list[DocumentResponse], status_code=201)
async def upload_documents(
    project_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    settings = get_settings()
    storage = get_storage_client()
    factory = get_parser_factory()
    documents = []

    for file in files:
        # Validate file type
        file_type = factory.detect_file_type(file.filename)
        if file_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.filename}. Supported: {factory.supported_formats()}",
            )

        # Read file data
        file_data = await file.read()

        # Check file size
        if len(file_data) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of {settings.max_upload_size_mb}MB",
            )

        # Upload to storage
        object_name = f"projects/{project_id}/documents/{uuid.uuid4()}/{file.filename}"
        content_type = factory.get_content_type(file.filename)
        storage.upload_file(object_name, file_data, content_type)

        # Create document record
        doc = Document(
            project_id=project_id,
            filename=file.filename,
            file_path=object_name,
            file_type=file_type,
            file_size_bytes=len(file_data),
            status="uploaded",
            uploaded_by=current_user.id,
        )
        db.add(doc)
        documents.append(doc)

    await db.flush()

    return [
        DocumentResponse(
            id=doc.id,
            project_id=doc.project_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            doc_category=doc.doc_category,
            page_count=doc.page_count,
            status=doc.status,
            error_message=doc.error_message,
            created_at=doc.created_at,
        )
        for doc in documents
    ]


@router.get("/projects/{project_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                project_id=doc.project_id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size_bytes=doc.file_size_bytes,
                doc_category=doc.doc_category,
                page_count=doc.page_count,
                status=doc.status,
                error_message=doc.error_message,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.post("/documents/{document_id}/parse", response_model=DocumentParseStatus)
async def parse_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger document parsing (synchronous for MVP, async via Celery in production)."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        doc.status = "parsing"
        await db.flush()

        # Download file from storage
        storage = get_storage_client()
        file_data = storage.download_file(doc.file_path)

        # Parse the document
        factory = get_parser_factory()
        parsed = factory.parse(file_data, doc.filename)

        # Classify the document
        from app.documents.classifier import classify_document

        category = classify_document(parsed.text, doc.filename, bool(parsed.tables))

        # Update document record
        doc.parsed_text = parsed.text
        doc.page_count = parsed.page_count
        doc.doc_category = category
        doc.status = "parsed"
        await db.flush()

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)
        await db.flush()

    return DocumentParseStatus(
        id=doc.id,
        status=doc.status,
        doc_category=doc.doc_category,
        page_count=doc.page_count,
        error_message=doc.error_message,
    )


@router.get("/documents/{document_id}/status", response_model=DocumentParseStatus)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentParseStatus(
        id=doc.id,
        status=doc.status,
        doc_category=doc.doc_category,
        page_count=doc.page_count,
        error_message=doc.error_message,
    )


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a document file from storage."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        storage = get_storage_client()
        file_data = storage.download_file(doc.file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {e}")

    # Determine content type
    content_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    content_type = content_types.get(doc.file_type, "application/octet-stream")

    return FastAPIResponse(
        content=file_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
        },
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its file from storage."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from S3 (best-effort — DB record deleted even if S3 fails)
    try:
        storage = get_storage_client()
        storage.delete_file(doc.file_path)
    except Exception as e:
        logger.warning(f"Failed to delete S3 file {doc.file_path}: {e}")

    # Delete from database
    await db.delete(doc)
