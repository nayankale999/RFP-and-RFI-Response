import logging

from app.tasks.celery_app import celery
from app.documents.parsers.factory import get_parser_factory
from app.documents.classifier import classify_document
from app.shared.storage import get_storage_client

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="parse_document")
def parse_document_task(self, document_id: str, file_path: str, filename: str):
    """Async task to parse a document and classify it."""
    logger.info(f"Parsing document: {filename} ({document_id})")

    try:
        # Download from storage
        storage = get_storage_client()
        file_data = storage.download_file(file_path)

        # Parse
        factory = get_parser_factory()
        parsed = factory.parse(file_data, filename)

        # Classify
        category = classify_document(parsed.text, filename, bool(parsed.tables))

        return {
            "status": "parsed",
            "document_id": document_id,
            "text_length": len(parsed.text),
            "page_count": parsed.page_count,
            "doc_category": category,
            "was_ocr": parsed.was_ocr,
            "table_count": len(parsed.tables),
        }

    except Exception as e:
        logger.error(f"Parse task failed for {document_id}: {e}")
        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e),
        }
