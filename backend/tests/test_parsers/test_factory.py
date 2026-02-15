import pytest
from app.documents.parsers.factory import ParserFactory
from app.documents.parsers.pdf_parser import PDFParser
from app.documents.parsers.docx_parser import DocxParser
from app.documents.parsers.xlsx_parser import XlsxParser
from app.documents.parsers.csv_parser import CsvParser
from app.documents.parsers.pptx_parser import PptxParser
from app.shared.exceptions import DocumentParsingError


class TestParserFactory:
    def setup_method(self):
        self.factory = ParserFactory()

    def test_get_pdf_parser(self):
        parser = self.factory.get_parser("document.pdf")
        assert isinstance(parser, PDFParser)

    def test_get_docx_parser(self):
        parser = self.factory.get_parser("document.docx")
        assert isinstance(parser, DocxParser)

    def test_get_xlsx_parser(self):
        parser = self.factory.get_parser("spreadsheet.xlsx")
        assert isinstance(parser, XlsxParser)

    def test_get_csv_parser(self):
        parser = self.factory.get_parser("data.csv")
        assert isinstance(parser, CsvParser)

    def test_get_pptx_parser(self):
        parser = self.factory.get_parser("presentation.pptx")
        assert isinstance(parser, PptxParser)

    def test_unsupported_format_raises(self):
        with pytest.raises(DocumentParsingError):
            self.factory.get_parser("file.xyz")

    def test_detect_file_type(self):
        assert ParserFactory.detect_file_type("doc.pdf") == "pdf"
        assert ParserFactory.detect_file_type("doc.docx") == "docx"
        assert ParserFactory.detect_file_type("doc.xlsx") == "xlsx"
        assert ParserFactory.detect_file_type("doc.csv") == "csv"
        assert ParserFactory.detect_file_type("doc.pptx") == "pptx"
        assert ParserFactory.detect_file_type("doc.unknown") == "unknown"

    def test_supported_formats(self):
        formats = self.factory.supported_formats()
        assert ".pdf" in formats
        assert ".docx" in formats
        assert ".xlsx" in formats
        assert ".csv" in formats
        assert ".pptx" in formats


class TestCsvParser:
    def test_parse_csv(self):
        parser = CsvParser()
        csv_data = b"Name,Age,City\nAlice,30,New York\nBob,25,London"
        result = parser.parse(csv_data, "test.csv")
        assert "Alice" in result.text
        assert "Bob" in result.text
        assert len(result.tables) == 1
        assert len(result.tables[0]) == 3  # header + 2 rows
        assert result.page_count == 1

    def test_parse_empty_csv(self):
        parser = CsvParser()
        result = parser.parse(b"", "empty.csv")
        assert result.text == ""

    def test_supported_extensions(self):
        parser = CsvParser()
        assert parser.supported_extensions() == [".csv"]
        assert parser.can_parse("data.csv")
        assert not parser.can_parse("data.xlsx")
