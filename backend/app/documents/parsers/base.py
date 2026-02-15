from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    """Standardized output from any document parser."""

    text: str
    page_count: int = 0
    metadata: dict = field(default_factory=dict)
    tables: list[list[list[str]]] = field(default_factory=list)  # list of tables, each table is rows of cells
    sections: list[dict] = field(default_factory=list)  # [{heading, level, content}]
    was_ocr: bool = False


class BaseParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def parse(self, file_data: bytes, filename: str) -> ParsedDocument:
        """Parse a document and return structured content."""
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions (e.g., ['.pdf'])."""
        pass

    def can_parse(self, filename: str) -> bool:
        """Check if this parser can handle the given file."""
        ext = self._get_extension(filename)
        return ext in self.supported_extensions()

    @staticmethod
    def _get_extension(filename: str) -> str:
        return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
