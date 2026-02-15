import json
import logging

import gspread
from google.oauth2.service_account import Credentials

from app.config import get_settings
from app.documents.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleSheetParser(BaseParser):
    """Google Sheets parser via Google API."""

    def supported_extensions(self) -> list[str]:
        return [".gsheet"]

    def parse(self, file_data: bytes, filename: str) -> ParsedDocument:
        """Parse a Google Sheet by its URL or ID.

        file_data should contain the sheet URL or ID as UTF-8 bytes.
        """
        settings = get_settings()
        sheet_ref = file_data.decode("utf-8").strip()

        try:
            creds_info = json.loads(settings.google_service_account_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            gc = gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Google auth failed: {e}")
            raise

        try:
            # Support both URLs and sheet IDs
            if sheet_ref.startswith("http"):
                spreadsheet = gc.open_by_url(sheet_ref)
            else:
                spreadsheet = gc.open_by_key(sheet_ref)
        except Exception as e:
            logger.error(f"Failed to open Google Sheet: {e}")
            raise

        all_text_parts = []
        all_tables = []

        for worksheet in spreadsheet.worksheets():
            all_text_parts.append(f"--- Sheet: {worksheet.title} ---")
            values = worksheet.get_all_values()
            rows = []
            for row in values:
                cells = [str(cell).strip() for cell in row]
                if any(c for c in cells):
                    rows.append(cells)
                    all_text_parts.append(" | ".join(cells))
            if rows:
                all_tables.append(rows)

        full_text = "\n".join(all_text_parts)
        return ParsedDocument(
            text=full_text,
            page_count=len(spreadsheet.worksheets()),
            tables=all_tables,
            metadata={
                "filename": filename,
                "parser": "gsheet",
                "spreadsheet_title": spreadsheet.title,
                "sheet_count": len(spreadsheet.worksheets()),
            },
        )
