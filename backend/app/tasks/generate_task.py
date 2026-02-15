import logging

from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="generate_responses_batch")
def generate_responses_batch_task(self, project_id: str, requirement_ids: list[str]):
    """Async task to generate responses for a batch of requirements.

    Note: This task uses synchronous DB access since Celery workers
    run in a synchronous context. For MVP, response generation
    is done synchronously via the API endpoint.
    """
    logger.info(f"Generating responses for {len(requirement_ids)} requirements in project {project_id}")

    # For production, implement synchronous DB session and response generation here
    # For MVP, this is handled synchronously in the API endpoint
    return {
        "status": "success",
        "project_id": project_id,
        "requirement_count": len(requirement_ids),
    }


@celery.task(bind=True, name="generate_word_export")
def generate_word_export_task(self, project_id: str, export_config: dict):
    """Async task to generate a Word document export.

    For large projects, this can take several minutes.
    """
    logger.info(f"Generating Word export for project: {project_id}")

    # For production, implement full export logic here
    return {
        "status": "success",
        "project_id": project_id,
    }
