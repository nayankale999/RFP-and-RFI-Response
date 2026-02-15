import csv
import io
import logging

from app.documents.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class CsvParser(BaseParser):
    """CSV file parser."""

    def supported_extensions(self) -> list[str]:
        return [".csv"]

    def parse(self, file_data: bytes, filename: str) -> ParsedDocument:
        try:
            # Try UTF-8 first, fall back to latin-1
            try:
                text_content = file_data.decode("utf-8")
            except UnicodeDecodeError:
                text_content = file_data.decode("latin-1")

            reader = csv.reader(io.StringIO(text_content))
            rows = []
            text_parts = []

            for row in reader:
                cells = [str(cell).strip() for cell in row]
                if any(c for c in cells):
                    rows.append(cells)
                    text_parts.append(" | ".join(cells))

            full_text = "\n".join(text_parts)
            return ParsedDocument(
                text=full_text,
                page_count=1,
                tables=[rows] if rows else [],
                metadata={
                    "filename": filename,
                    "parser": "csv",
                    "row_count": len(rows),
                },
            )
        except Exception as e:
            logger.error(f"Failed to parse CSV {filename}: {e}")
            raise
