import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.pricing import PricingItem, ScheduleEvent, ResponsePlan
from app.models.project import Project
from app.models.document import Document
from app.models.requirement import Requirement
from app.models.user import User
from app.api.auth import get_current_user
from app.extraction.schedule_extractor import extract_schedule
from app.extraction.pricing_extractor import extract_pricing_structure
from app.responses.plan_generator import generate_response_plan

router = APIRouter(prefix="/api", tags=["pricing & schedule"])


# --- Schedule endpoints ---

class ScheduleEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    event_name: str
    event_date: str | None
    notes: str | None

    model_config = {"from_attributes": True}


@router.get("/projects/{project_id}/schedule", response_model=list[ScheduleEventOut])
async def get_schedule(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScheduleEvent).where(ScheduleEvent.project_id == project_id)
    )
    events = result.scalars().all()
    return [
        ScheduleEventOut(
            id=e.id,
            event_type=e.event_type,
            event_name=e.event_name,
            event_date=str(e.event_date) if e.event_date else None,
            notes=e.notes,
        )
        for e in events
    ]


@router.post("/projects/{project_id}/schedule/extract")
async def extract_schedule_events(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract schedule events from parsed documents."""
    result = await db.execute(
        select(Document).where(Document.project_id == project_id, Document.status.in_(["parsed", "extracted"]))
    )
    documents = result.scalars().all()

    if not documents:
        raise HTTPException(status_code=400, detail="No parsed documents found")

    # Combine text from all documents for schedule extraction
    combined_text = "\n\n".join(doc.parsed_text for doc in documents if doc.parsed_text)

    events = extract_schedule(combined_text)
    count = 0

    for event_data in events:
        from datetime import date as date_type

        event_date = None
        date_str = event_data.get("date")
        if date_str and date_str != "null":
            try:
                event_date = date_type.fromisoformat(date_str)
            except (ValueError, TypeError):
                pass

        event = ScheduleEvent(
            project_id=project_id,
            event_type=event_data.get("event_type", "other"),
            event_name=event_data.get("event_name", "Unknown Event"),
            event_date=event_date,
            notes=event_data.get("notes"),
        )
        db.add(event)
        count += 1

    await db.flush()
    return {"message": f"Extracted {count} schedule events"}


# --- Pricing endpoints ---

class PricingItemCreate(BaseModel):
    category: str
    line_item: str
    description: str | None = None
    unit_cost: float | None = None
    quantity: int | None = None
    total: float | None = None
    currency: str = "USD"
    year: int | None = None
    notes: str | None = None


class PricingItemOut(BaseModel):
    id: uuid.UUID
    category: str
    line_item: str
    description: str | None
    unit_cost: float | None
    quantity: int | None
    total: float | None
    currency: str
    year: int | None
    notes: str | None

    model_config = {"from_attributes": True}


@router.get("/projects/{project_id}/pricing", response_model=list[PricingItemOut])
async def get_pricing(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PricingItem).where(PricingItem.project_id == project_id)
    )
    items = result.scalars().all()
    return [PricingItemOut.model_validate(item) for item in items]


@router.post("/projects/{project_id}/pricing", response_model=PricingItemOut, status_code=201)
async def add_pricing_item(
    project_id: uuid.UUID,
    request: PricingItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = PricingItem(
        project_id=project_id,
        **request.model_dump(),
    )
    db.add(item)
    await db.flush()
    return PricingItemOut.model_validate(item)


@router.put("/pricing/{item_id}", response_model=PricingItemOut)
async def update_pricing_item(
    item_id: uuid.UUID,
    request: PricingItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(PricingItem).where(PricingItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Pricing item not found")

    for field, value in request.model_dump().items():
        setattr(item, field, value)
    await db.flush()
    return PricingItemOut.model_validate(item)


# --- Response Plan endpoints ---

class ResponsePlanOut(BaseModel):
    id: uuid.UUID
    workstreams: dict | None
    escalation_matrix: dict | None
    version: int
    notes: str | None

    model_config = {"from_attributes": True}


@router.post("/projects/{project_id}/plan/generate", response_model=ResponsePlanOut)
async def generate_plan(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate an internal response plan for the project."""
    # Get requirements summary
    from sqlalchemy import func

    result = await db.execute(
        select(Requirement.type, func.count(Requirement.id))
        .where(Requirement.project_id == project_id)
        .group_by(Requirement.type)
    )
    type_counts = dict(result.all())
    total = sum(type_counts.values())

    # Get schedule events
    sched_result = await db.execute(
        select(ScheduleEvent).where(ScheduleEvent.project_id == project_id)
    )
    events = sched_result.scalars().all()
    event_dicts = [
        {"event_type": e.event_type, "event_name": e.event_name, "date": str(e.event_date) if e.event_date else "TBD"}
        for e in events
    ]

    # Get project name
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate plan
    plan_data = generate_response_plan(
        requirements_summary={"type_counts": type_counts, "total": total},
        schedule_events=event_dicts,
        project_name=project.name,
    )

    # Save or update plan
    existing = await db.execute(
        select(ResponsePlan).where(ResponsePlan.project_id == project_id)
    )
    plan = existing.scalar_one_or_none()

    if plan:
        plan.workstreams = plan_data.get("workstreams")
        plan.escalation_matrix = plan_data.get("escalation_matrix")
        plan.notes = "\n".join(plan_data.get("collaboration_notes", []))
        plan.version += 1
    else:
        plan = ResponsePlan(
            project_id=project_id,
            owner_id=current_user.id,
            workstreams=plan_data.get("workstreams"),
            escalation_matrix=plan_data.get("escalation_matrix"),
            notes="\n".join(plan_data.get("collaboration_notes", [])),
        )
        db.add(plan)

    await db.flush()
    return ResponsePlanOut.model_validate(plan)
