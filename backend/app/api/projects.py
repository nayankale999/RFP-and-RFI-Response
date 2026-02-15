import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.document import Document
from app.models.requirement import Requirement
from app.models.response import Response
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        name=request.name,
        description=request.description,
        client_name=request.client_name,
        industry=request.industry,
        deadline=request.deadline,
        owner_id=current_user.id,
    )
    db.add(project)
    await db.flush()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        client_name=project.client_name,
        industry=project.industry,
        deadline=project.deadline,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()

    count_result = await db.execute(select(func.count(Project.id)))
    total = count_result.scalar() or 0

    items = []
    for p in projects:
        doc_count = await db.execute(
            select(func.count(Document.id)).where(Document.project_id == p.id)
        )
        req_count = await db.execute(
            select(func.count(Requirement.id)).where(Requirement.project_id == p.id)
        )
        resp_count = await db.execute(
            select(func.count(Response.id)).where(Response.project_id == p.id)
        )
        items.append(
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                status=p.status,
                client_name=p.client_name,
                industry=p.industry,
                deadline=p.deadline,
                owner_id=p.owner_id,
                created_at=p.created_at,
                updated_at=p.updated_at,
                document_count=doc_count.scalar() or 0,
                requirement_count=req_count.scalar() or 0,
                response_count=resp_count.scalar() or 0,
            )
        )

    return ProjectListResponse(projects=items, total=total)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    doc_count = await db.execute(
        select(func.count(Document.id)).where(Document.project_id == project.id)
    )
    req_count = await db.execute(
        select(func.count(Requirement.id)).where(Requirement.project_id == project.id)
    )
    resp_count = await db.execute(
        select(func.count(Response.id)).where(Response.project_id == project.id)
    )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        client_name=project.client_name,
        industry=project.industry,
        deadline=project.deadline,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=doc_count.scalar() or 0,
        requirement_count=req_count.scalar() or 0,
        response_count=resp_count.scalar() or 0,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    request: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        client_name=project.client_name,
        industry=project.industry,
        deadline=project.deadline,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
