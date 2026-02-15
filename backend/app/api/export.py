import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.database import get_db
from app.models.project import Project
from app.models.document import Document
from app.models.requirement import Requirement
from app.models.response import Response
from app.models.pricing import ScheduleEvent, PricingItem, ResponsePlan
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.export import ExportRequest
from app.export.word_generator import generate_word_document
from app.responses.compliance_scorer import calculate_compliance_scores

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/projects/{project_id}/export/word")
async def export_word(
    project_id: uuid.UUID,
    request: ExportRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download the RFP response as a Word document."""
    if request is None:
        request = ExportRequest()

    # Fetch project
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch all related data
    req_result = await db.execute(
        select(Requirement).where(Requirement.project_id == project_id).order_by(Requirement.req_number)
    )
    requirements = req_result.scalars().all()

    resp_result = await db.execute(
        select(Response).where(Response.project_id == project_id)
    )
    responses = resp_result.scalars().all()

    sched_result = await db.execute(
        select(ScheduleEvent).where(ScheduleEvent.project_id == project_id)
    )
    schedule = sched_result.scalars().all()

    price_result = await db.execute(
        select(PricingItem).where(PricingItem.project_id == project_id)
    )
    pricing = price_result.scalars().all()

    # Calculate compliance scores
    req_dicts = [{"id": str(r.id), "type": r.type, "is_mandatory": r.is_mandatory} for r in requirements]
    resp_dicts = [
        {"requirement_id": str(r.requirement_id), "compliance_status": r.compliance_status}
        for r in responses
    ]
    scores = calculate_compliance_scores(req_dicts, resp_dicts)

    # Build context for Word generation
    context = {
        "project": {
            "name": project.name,
            "description": project.description,
            "client_name": project.client_name or "Client",
            "industry": project.industry,
            "status": project.status,
        },
        "company": {
            "name": request.company_name,
            "description": request.company_description,
        },
        "requirements": [
            {
                "id": str(r.id),
                "req_number": r.req_number,
                "title": r.title,
                "description": r.description,
                "type": r.type,
                "category": r.category,
                "is_mandatory": r.is_mandatory,
                "priority": r.priority,
            }
            for r in requirements
        ],
        "responses": [
            {
                "requirement_id": str(r.requirement_id),
                "compliance_status": r.compliance_status,
                "response_text": r.response_text,
                "confidence_score": r.confidence_score,
                "is_reviewed": r.is_reviewed,
            }
            for r in responses
        ],
        "schedule": [
            {
                "event_name": s.event_name,
                "event_type": s.event_type,
                "date": str(s.event_date) if s.event_date else "TBD",
                "notes": s.notes or "",
            }
            for s in schedule
        ],
        "pricing": [
            {
                "category": p.category,
                "line_item": p.line_item,
                "description": p.description,
                "unit_cost": p.unit_cost,
                "quantity": p.quantity,
                "total": p.total,
                "currency": p.currency,
            }
            for p in pricing
        ],
        "compliance_scores": scores,
    }

    # Generate Word document
    doc_bytes = generate_word_document(context)

    # Return as downloadable file
    filename = f"RFP_Response_{project.name.replace(' ', '_')}.docx"
    return StreamingResponse(
        io.BytesIO(doc_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
