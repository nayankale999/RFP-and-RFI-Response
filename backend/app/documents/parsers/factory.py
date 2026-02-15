import logging

from app.documents.parsers.base import BaseParser, ParsedDocument
from app.documents.parsers.pdf_parser import PDFParser
from app.documents.parsers.docx_parser import DocxParser
from app.documents.parsers.xlsx_parser import XlsxParser
from app.documents.parsers.csv_parser import CsvParser
from app.documents.parsers.pptx_parser import PptxParser
from app.documents.parsers.gsheet_parser import GoogleSheetParser
from app.shared.exceptions import DocumentParsingError

logger = logging.getLogger(__name__)

# File extension to MIME type mapping
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
}


class ParserFactory:
    """Factory that selects the correct parser based on file type."""

    def __init__(self):
        self._parsers: list[BaseParser] = [
            PDFParser(),
            DocxParser(),
            XlsxParser(),
            CsvParser(),
            PptxParser(),
            GoogleSheetParser(),
        ]

    def get_parser(self, filename: str) -> BaseParser:
        """Get the appropriate parser for a file."""
        for parser in self._parsers:
            if parser.can_parse(filename):
                return parser
        raise DocumentParsingError(
            f"No parser available for file: {filename}",
            detail=f"Supported formats: {self.supported_formats()}",
        )

    def parse(self, file_data: bytes, filename: str) -> ParsedDocument:
        """Parse a document using the appropriate parser."""
        parser = self.get_parser(filename)
        logger.info(f"Parsing {filename} with {parser.__class__.__name__}")
        try:
            return parser.parse(file_data, filename)
        except DocumentParsingError:
            raise
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse {filename}: {str(e)}",
                detail=str(e),
            )

    def supported_formats(self) -> list[str]:
        """Return all supported file extensions."""
        extensions = []
        for parser in self._parsers:
            extensions.extend(parser.supported_extensions())
        return extensions

    @staticmethod
    def detect_file_type(filename: str) -> str:
        """Detect file type from filename extension."""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        type_map = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".doc": "docx",
            ".xlsx": "xlsx",
            ".xls": "xlsx",
            ".csv": "csv",
            ".pptx": "pptx",
            ".ppt": "pptx",
            ".gsheet": "gsheet",
        }
        return type_map.get(ext, "unknown")

    @staticmethod
    def get_content_type(filename: str) -> str:
        """Get MIME content type for a file."""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return CONTENT_TYPES.get(ext, "application/octet-stream")


# Singleton
_parser_factory: ParserFactory | None = None


def get_parser_factory() -> ParserFactory:
    global _parser_factory
    if _parser_factory is None:
        _parser_factory = ParserFactory()
    return _parser_factory
