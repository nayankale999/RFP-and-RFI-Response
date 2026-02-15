import io
import logging

import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from app.documents.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """PDF parser with OCR fallback for scanned documents."""

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_data: bytes, filename: str) -> ParsedDocument:
        pages_text = []
        all_tables = []
        page_count = 0
        was_ocr = False

        try:
            with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                page_count = len(pdf.pages)

                for page in pdf.pages:
                    text = page.extract_text() or ""

                    # If page has very little text, try OCR
                    if len(text.strip()) < 50:
                        ocr_text = self._ocr_page(file_data, page.page_number - 1)
                        if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                            text = ocr_text
                            was_ocr = True

                    pages_text.append(text)

                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        cleaned = [[str(cell) if cell else "" for cell in row] for row in table]
                        all_tables.append(cleaned)

        except Exception as e:
            logger.warning(f"pdfplumber failed for {filename}, falling back to full OCR: {e}")
            pages_text, page_count = self._full_ocr(file_data)
            was_ocr = True

        full_text = "\n\n".join(pages_text)
        return ParsedDocument(
            text=full_text,
            page_count=page_count,
            tables=all_tables,
            was_ocr=was_ocr,
            metadata={"filename": filename, "parser": "pdf"},
        )

    def _ocr_page(self, file_data: bytes, page_index: int) -> str:
        """OCR a single page."""
        try:
            images = convert_from_bytes(file_data, first_page=page_index + 1, last_page=page_index + 1)
            if images:
                return pytesseract.image_to_string(images[0])
        except Exception as e:
            logger.warning(f"OCR failed for page {page_index}: {e}")
        return ""

    def _full_ocr(self, file_data: bytes) -> tuple[list[str], int]:
        """OCR the entire PDF."""
        try:
            images = convert_from_bytes(file_data)
            pages = [pytesseract.image_to_string(img) for img in images]
            return pages, len(images)
        except Exception as e:
            logger.error(f"Full OCR failed: {e}")
            return [""], 0
