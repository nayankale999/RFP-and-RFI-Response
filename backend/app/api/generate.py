import uuid
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.document import Document
from app.models.user import User
from app.api.auth import get_current_user
from app.orchestrator.pipeline import GenerationPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generate"])


async def _run_pipeline_background(project_id: uuid.UUID):
    """Background task to run the generation pipeline."""
    try:
        pipeline = GenerationPipeline(project_id)
        await pipeline.run()
    except Exception as e:
        logger.exception(f"Pipeline background task failed: {e}")


@router.post("/projects/{project_id}/generate-full")
async def generate_full(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger the full generation pipeline (Win Plan + Answer RFP + RFI Response PDF).

    Returns immediately and runs processing in background.
    Poll GET /projects/{project_id} to check processing_status.
    """
    # Verify project exists
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already processing
    if project.processing_status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Generation is already in progress for this project"
        )

    # Verify project has documents
    result = await db.execute(
        select(Document).where(Document.project_id == project_id)
    )
    documents = result.scalars().all()
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded. Upload documents before generating."
        )

    # Set processing status
    project.processing_status = "processing"
    project.processing_message = "Generation queued..."
    project.processing_started_at = datetime.now(timezone.utc)
    await db.commit()

    # Launch as async task on the event loop (not BackgroundTasks)
    # This properly supports SQLAlchemy async sessions
    asyncio.create_task(_run_pipeline_background(project_id))

    return {
        "message": "Generation started",
        "processing_status": "processing",
        "project_id": str(project_id),
    }
