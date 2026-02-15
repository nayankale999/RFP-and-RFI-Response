import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.document import Document
from app.models.requirement import Requirement
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.requirement import RequirementResponse, RequirementUpdate, RequirementListResponse
from app.extraction.requirement_extractor import extract_requirements
from app.shared.embedding_client import get_embedding_client

router = APIRouter(prefix="/api", tags=["requirements"])


@router.get("/projects/{project_id}/requirements", response_model=RequirementListResponse)
async def list_requirements(
    project_id: uuid.UUID,
    req_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Requirement).where(Requirement.project_id == project_id)
    if req_type:
        query = query.where(Requirement.type == req_type)
    query = query.order_by(Requirement.req_number)

    result = await db.execute(query)
    requirements = result.scalars().all()

    # Calculate type counts
    count_result = await db.execute(
        select(Requirement.type, func.count(Requirement.id))
        .where(Requirement.project_id == project_id)
        .group_by(Requirement.type)
    )
    type_counts = dict(count_result.all())

    return RequirementListResponse(
        requirements=[
            RequirementResponse(
                id=r.id,
                project_id=r.project_id,
                document_id=r.document_id,
                req_number=r.req_number,
                title=r.title,
                description=r.description,
                type=r.type,
                category=r.category,
                is_mandatory=r.is_mandatory,
                reference_page=r.reference_page,
                reference_section=r.reference_section,
                response_required=r.response_required,
                priority=r.priority,
                confidence_score=r.confidence_score,
                created_at=r.created_at,
            )
            for r in requirements
        ],
        total=len(requirements),
        type_counts=type_counts,
    )


@router.put("/requirements/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: uuid.UUID,
    request: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(req, field, value)
    await db.flush()

    return RequirementResponse(
        id=req.id,
        project_id=req.project_id,
        document_id=req.document_id,
        req_number=req.req_number,
        title=req.title,
        description=req.description,
        type=req.type,
        category=req.category,
        is_mandatory=req.is_mandatory,
        reference_page=req.reference_page,
        reference_section=req.reference_section,
        response_required=req.response_required,
        priority=req.priority,
        confidence_score=req.confidence_score,
        created_at=req.created_at,
    )


@router.post("/projects/{project_id}/extract")
async def trigger_extraction(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract requirements from all parsed documents in the project."""
    # Get all parsed documents
    result = await db.execute(
        select(Document).where(Document.project_id == project_id, Document.status == "parsed")
    )
    documents = result.scalars().all()

    if not documents:
        raise HTTPException(status_code=400, detail="No parsed documents found. Parse documents first.")

    total_extracted = 0
    embedding_client = get_embedding_client()

    for doc in documents:
        if not doc.parsed_text:
            continue

        # Extract requirements from this document
        raw_requirements = extract_requirements(doc.parsed_text, str(doc.id))

        # Create requirement records with embeddings
        for req_data in raw_requirements:
            # Generate embedding
            req_text = f"{req_data.get('title', '')} {req_data.get('description', '')}"
            try:
                embedding = embedding_client.embed_text(req_text)
            except Exception:
                embedding = None

            requirement = Requirement(
                project_id=project_id,
                document_id=doc.id,
                req_number=req_data.get("req_number", f"REQ-{total_extracted + 1:03d}"),
                title=req_data.get("title", "Untitled"),
                description=req_data.get("description", ""),
                type=req_data.get("type", "functional"),
                category=req_data.get("category"),
                is_mandatory=req_data.get("is_mandatory", True),
                reference_section=req_data.get("reference_section"),
                response_required=req_data.get("response_required", True),
                priority=req_data.get("priority", "medium"),
                embedding=embedding,
            )
            db.add(requirement)
            total_extracted += 1

        doc.status = "extracted"

    await db.flush()

    return {"message": f"Extracted {total_extracted} requirements from {len(documents)} documents"}
