import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.requirement import Requirement
from app.models.response import Response
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.response import ResponseOut, ResponseUpdate, ResponseListOut, ComplianceScoresOut
from app.responses.generator import generate_response, generate_responses_batch
from app.responses.compliance_scorer import calculate_compliance_scores

router = APIRouter(prefix="/api", tags=["responses"])


@router.get("/projects/{project_id}/responses", response_model=ResponseListOut)
async def list_responses(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Response).where(Response.project_id == project_id).order_by(Response.created_at)
    )
    responses = result.scalars().all()

    # Calculate compliance scores
    req_result = await db.execute(
        select(Requirement).where(Requirement.project_id == project_id)
    )
    requirements = req_result.scalars().all()

    req_dicts = [{"id": str(r.id), "type": r.type, "is_mandatory": r.is_mandatory} for r in requirements]
    resp_dicts = [
        {"requirement_id": str(r.requirement_id), "compliance_status": r.compliance_status}
        for r in responses
    ]
    scores = calculate_compliance_scores(req_dicts, resp_dicts)

    return ResponseListOut(
        responses=[
            ResponseOut(
                id=r.id,
                requirement_id=r.requirement_id,
                project_id=r.project_id,
                compliance_status=r.compliance_status,
                response_text=r.response_text,
                confidence_score=r.confidence_score,
                source_refs=r.source_refs,
                is_ai_generated=r.is_ai_generated,
                is_reviewed=r.is_reviewed,
                reviewed_by=r.reviewed_by,
                reviewed_at=r.reviewed_at,
                notes=r.notes,
                created_at=r.created_at,
            )
            for r in responses
        ],
        total=len(responses),
        compliance_scores=scores,
    )


@router.put("/responses/{response_id}", response_model=ResponseOut)
async def update_response(
    response_id: uuid.UUID,
    request: ResponseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Response).where(Response.id == response_id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resp, field, value)

    # If marking as reviewed, set reviewer info
    if request.is_reviewed:
        resp.reviewed_by = current_user.id
        resp.reviewed_at = datetime.now(timezone.utc)
        resp.is_ai_generated = False

    await db.flush()

    return ResponseOut(
        id=resp.id,
        requirement_id=resp.requirement_id,
        project_id=resp.project_id,
        compliance_status=resp.compliance_status,
        response_text=resp.response_text,
        confidence_score=resp.confidence_score,
        source_refs=resp.source_refs,
        is_ai_generated=resp.is_ai_generated,
        is_reviewed=resp.is_reviewed,
        reviewed_by=resp.reviewed_by,
        reviewed_at=resp.reviewed_at,
        notes=resp.notes,
        created_at=resp.created_at,
    )


@router.post("/projects/{project_id}/generate")
async def trigger_response_generation(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI responses for all requirements that don't have responses yet."""
    # Get requirements without responses
    result = await db.execute(
        select(Requirement)
        .where(Requirement.project_id == project_id, Requirement.response_required == True)
        .order_by(Requirement.req_number)
    )
    requirements = result.scalars().all()

    # Get existing response requirement IDs
    existing = await db.execute(
        select(Response.requirement_id).where(Response.project_id == project_id)
    )
    existing_ids = {row[0] for row in existing.all()}

    # Filter to requirements without responses
    pending_reqs = [r for r in requirements if r.id not in existing_ids]

    if not pending_reqs:
        return {"message": "All requirements already have responses", "generated": 0}

    # Generate responses
    req_dicts = [
        {
            "id": str(r.id),
            "req_number": r.req_number,
            "title": r.title,
            "description": r.description,
            "type": r.type,
            "category": r.category,
            "is_mandatory": r.is_mandatory,
        }
        for r in pending_reqs
    ]

    generated_responses = await generate_responses_batch(req_dicts, db, current_user.org_id if hasattr(current_user, 'org_id') else None)

    # Save responses
    count = 0
    for req, gen_resp in zip(pending_reqs, generated_responses):
        response = Response(
            requirement_id=req.id,
            project_id=project_id,
            compliance_status=gen_resp.get("compliance_status", "custom_dev"),
            response_text=gen_resp.get("response_text", ""),
            confidence_score=gen_resp.get("confidence_score"),
            source_refs=gen_resp.get("source_refs"),
            is_ai_generated=True,
            notes=gen_resp.get("notes"),
        )
        db.add(response)
        count += 1

    await db.flush()

    return {"message": f"Generated {count} responses", "generated": count, "total_requirements": len(requirements)}


@router.post("/responses/{response_id}/regenerate", response_model=ResponseOut)
async def regenerate_response(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a single AI response."""
    result = await db.execute(select(Response).where(Response.id == response_id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")

    # Get the requirement
    req_result = await db.execute(select(Requirement).where(Requirement.id == resp.requirement_id))
    requirement = req_result.scalar_one_or_none()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    req_dict = {
        "id": str(requirement.id),
        "req_number": requirement.req_number,
        "title": requirement.title,
        "description": requirement.description,
        "type": requirement.type,
        "category": requirement.category,
        "is_mandatory": requirement.is_mandatory,
    }

    gen_resp = await generate_response(req_dict, db)

    resp.compliance_status = gen_resp.get("compliance_status", resp.compliance_status)
    resp.response_text = gen_resp.get("response_text", resp.response_text)
    resp.confidence_score = gen_resp.get("confidence_score")
    resp.source_refs = gen_resp.get("source_refs")
    resp.is_ai_generated = True
    resp.is_reviewed = False

    await db.flush()

    return ResponseOut(
        id=resp.id,
        requirement_id=resp.requirement_id,
        project_id=resp.project_id,
        compliance_status=resp.compliance_status,
        response_text=resp.response_text,
        confidence_score=resp.confidence_score,
        source_refs=resp.source_refs,
        is_ai_generated=resp.is_ai_generated,
        is_reviewed=resp.is_reviewed,
        reviewed_by=resp.reviewed_by,
        reviewed_at=resp.reviewed_at,
        notes=resp.notes,
        created_at=resp.created_at,
    )
