import logging

from app.tasks.celery_app import celery
from app.extraction.requirement_extractor import extract_requirements
from app.extraction.schedule_extractor import extract_schedule
from app.extraction.pricing_extractor import extract_pricing_structure

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="extract_requirements")
def extract_requirements_task(self, document_id: str, text: str):
    """Async task to extract requirements from parsed document text."""
    logger.info(f"Extracting requirements from document: {document_id}")

    try:
        requirements = extract_requirements(text, document_id)
        return {
            "status": "success",
            "document_id": document_id,
            "requirement_count": len(requirements),
            "requirements": requirements,
        }
    except Exception as e:
        logger.error(f"Extraction failed for {document_id}: {e}")
        return {"status": "failed", "document_id": document_id, "error": str(e)}


@celery.task(bind=True, name="extract_schedule")
def extract_schedule_task(self, project_id: str, text: str):
    """Async task to extract schedule events."""
    logger.info(f"Extracting schedule for project: {project_id}")

    try:
        events = extract_schedule(text)
        return {
            "status": "success",
            "project_id": project_id,
            "event_count": len(events),
            "events": events,
        }
    except Exception as e:
        logger.error(f"Schedule extraction failed for {project_id}: {e}")
        return {"status": "failed", "project_id": project_id, "error": str(e)}


@celery.task(bind=True, name="extract_pricing")
def extract_pricing_task(self, project_id: str, text: str):
    """Async task to extract pricing structure."""
    logger.info(f"Extracting pricing for project: {project_id}")

    try:
        pricing = extract_pricing_structure(text)
        return {
            "status": "success",
            "project_id": project_id,
            "pricing": pricing,
        }
    except Exception as e:
        logger.error(f"Pricing extraction failed for {project_id}: {e}")
        return {"status": "failed", "project_id": project_id, "error": str(e)}
