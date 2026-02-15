#!/usr/bin/env python3
"""
RFI Response PDF Generator

Generates a professional RFI response PDF document with corporate branding,
modeled after the DBW Risk Management Solution RFI Response format.

Usage:
    python3 generate_pdf.py --input data.json --output response.pdf [--verbose]
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Flowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.27 x 841.89 pts
MARGIN_LEFT = 72  # 1 inch
MARGIN_RIGHT = 72
MARGIN_TOP = 72
MARGIN_BOTTOM = 72
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # ~451 pts

# Colors from the reference document
HEADING_BAR_COLOR = HexColor("#314662")
FOOTER_TEXT_COLOR = HexColor("#1f3863")
LINK_COLOR = HexColor("#0462c1")
TABLE_HEADER_BG = HexColor("#D9D9D9")
COVER_BG_DEFAULT = HexColor("#1B3A5C")
BODY_TEXT_COLOR = black
WHITE = white

# Heading bar dimensions
HEADING_BAR_HEIGHT = 28
HEADING_BAR_PADDING = 8


# ---------------------------------------------------------------------------
# Font Manager
# ---------------------------------------------------------------------------

class FontManager:
    """Discovers and registers fonts across platforms with fallback logic."""

    FONT_SEARCH_PATHS = [
        # macOS
        "/System/Library/Fonts/Supplemental/",
        "/System/Library/Fonts/",
        "/Library/Fonts/",
        os.path.expanduser("~/Library/Fonts/"),
        # Linux
        "/usr/share/fonts/truetype/",
        "/usr/share/fonts/truetype/msttcorefonts/",
        "/usr/share/fonts/",
        "/usr/local/share/fonts/",
        os.path.expanduser("~/.fonts/"),
        # Windows
        "C:\\Windows\\Fonts\\",
    ]

    FONT_DEFINITIONS = {
        "CalibriLight": {
            "files": ["calibril.ttf", "Calibri-Light.ttf", "CalibriLight.ttf", "calibri-light.ttf"],
            "fallback_files": ["Arial.ttf", "arial.ttf", "LiberationSans-Regular.ttf"],
            "builtin_fallback": "Helvetica",
        },
        "CalibriLightBold": {
            "files": ["calibrib.ttf", "Calibri-Bold.ttf", "CalibriBold.ttf"],
            "fallback_files": ["Arial Bold.ttf", "arialbd.ttf", "LiberationSans-Bold.ttf"],
            "builtin_fallback": "Helvetica-Bold",
        },
        "TimesNewRoman": {
            "files": [
                "Times New Roman.ttf", "times.ttf", "TimesNewRoman.ttf",
                "Times New Roman Regular.ttf", "timesNewRoman.ttf",
            ],
            "fallback_files": ["Georgia.ttf", "georgia.ttf", "LiberationSerif-Regular.ttf"],
            "builtin_fallback": "Times-Roman",
        },
        "TimesNewRomanBold": {
            "files": [
                "Times New Roman Bold.ttf", "timesbd.ttf", "TimesNewRomanBold.ttf",
                "Times New Roman Bold Regular.ttf",
            ],
            "fallback_files": ["Georgia Bold.ttf", "georgiab.ttf", "LiberationSerif-Bold.ttf"],
            "builtin_fallback": "Times-Bold",
        },
        "TimesNewRomanItalic": {
            "files": [
                "Times New Roman Italic.ttf", "timesi.ttf", "TimesNewRomanItalic.ttf",
            ],
            "fallback_files": ["Georgia Italic.ttf", "georgiai.ttf", "LiberationSerif-Italic.ttf"],
            "builtin_fallback": "Times-Italic",
        },
    }

    def __init__(self):
        self.font_map: dict[str, str] = {}
        self.substitutions: dict[str, str] = {}

    def register_fonts(self) -> dict[str, str]:
        """Register all required fonts, returning a mapping of logical names to registered names."""
        for logical_name, defn in self.FONT_DEFINITIONS.items():
            registered = self._try_register(logical_name, defn["files"])
            if not registered:
                registered = self._try_register(logical_name, defn["fallback_files"])
                if registered:
                    self.substitutions[logical_name] = registered
            if not registered:
                # Use ReportLab built-in
                self.font_map[logical_name] = defn["builtin_fallback"]
                self.substitutions[logical_name] = defn["builtin_fallback"]
                logger.info(f"Font '{logical_name}' -> builtin '{defn['builtin_fallback']}'")
            else:
                self.font_map[logical_name] = logical_name

        return self.font_map

    def _try_register(self, name: str, filenames: list[str]) -> Optional[str]:
        """Try to find and register a TTF font from the search paths."""
        for search_path in self.FONT_SEARCH_PATHS:
            if not os.path.isdir(search_path):
                continue
            for filename in filenames:
                font_path = os.path.join(search_path, filename)
                if os.path.isfile(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(name, font_path))
                        logger.info(f"Registered font '{name}' from '{font_path}'")
                        return name
                    except Exception as e:
                        logger.debug(f"Failed to register '{font_path}': {e}")
        return None

    def get(self, logical_name: str) -> str:
        """Get the registered font name for a logical name."""
        return self.font_map.get(logical_name, "Helvetica")


# ---------------------------------------------------------------------------
# Custom Flowables
# ---------------------------------------------------------------------------

class HeadingBarFlowable(Flowable):
    """A dark blue rectangle with white text, matching the reference document's section headings."""

    def __init__(self, text: str, font_name: str = "Helvetica", font_size: float = 18,
                 bar_height: float = HEADING_BAR_HEIGHT, bar_color=HEADING_BAR_COLOR):
        super().__init__()
        self.text = text
        self.font_name = font_name
        self.font_size = font_size
        self.bar_height = bar_height
        self.bar_color = bar_color
        self.width = CONTENT_WIDTH
        self.height = bar_height + 4  # a little padding below

    def draw(self):
        c = self.canv
        # Draw the filled rectangle
        c.setFillColor(self.bar_color)
        c.setStrokeColor(self.bar_color)
        c.rect(0, 4, self.width, self.bar_height, fill=1, stroke=0)

        # Draw white text on top
        c.setFillColor(WHITE)
        c.setFont(self.font_name, self.font_size)
        text_y = 4 + (self.bar_height - self.font_size) / 2 + 2
        c.drawString(HEADING_BAR_PADDING, text_y, self.text)


class CoverPageFlowable(Flowable):
    """Full-page cover with dark background and centered white text."""

    def __init__(self, data: dict, font_map: dict[str, str],
                 bg_color=COVER_BG_DEFAULT, bg_image_path: Optional[str] = None):
        super().__init__()
        self.data = data
        self.font_map = font_map
        self.bg_color = bg_color
        self.bg_image_path = bg_image_path
        self.width = PAGE_WIDTH
        self.height = PAGE_HEIGHT

    def draw(self):
        c = self.canv

        # Frame is full-page (0,0 origin, no padding), so draw directly
        # Draw background
        if self.bg_image_path and os.path.isfile(self.bg_image_path):
            try:
                c.drawImage(
                    self.bg_image_path,
                    0, 0,
                    width=PAGE_WIDTH, height=PAGE_HEIGHT,
                    preserveAspectRatio=False,
                )
            except Exception:
                # Fallback to solid color
                c.setFillColor(self.bg_color)
                c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        else:
            c.setFillColor(self.bg_color)
            c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

        # Title text - client name
        heading_font = self.font_map.get("CalibriLight", "Helvetica")
        client_name = self.data.get("client_name", "Client Name")
        solution_name = self.data.get("solution_name", "Solution Name")
        rfi_desc = self.data.get("rfi_description", "RFI Response")

        center_x = PAGE_WIDTH / 2

        # Client name at ~50% from bottom
        c.setFillColor(WHITE)
        c.setFont(heading_font, 36)
        c.drawCentredString(center_x, PAGE_HEIGHT * 0.50, client_name)

        # Solution name
        c.setFont(heading_font, 20)
        c.drawCentredString(center_x, PAGE_HEIGHT * 0.43, solution_name)

        # RFI description
        c.drawCentredString(center_x, PAGE_HEIGHT * 0.38, rfi_desc)


class TOCEntryFlowable(Flowable):
    """A single TOC entry with dot leaders and page number."""

    def __init__(self, section_name: str, page_num: int, font_name: str = "Times-Roman",
                 font_size: float = 12):
        super().__init__()
        self.section_name = section_name
        self.page_num = page_num
        self.font_name = font_name
        self.font_size = font_size
        self.width = CONTENT_WIDTH
        self.height = 20

    def draw(self):
        c = self.canv
        c.setFillColor(BODY_TEXT_COLOR)
        c.setFont(self.font_name, self.font_size)

        # Draw section name on left
        c.drawString(0, 4, self.section_name)

        # Draw page number on right
        page_str = str(self.page_num)
        page_width = c.stringWidth(page_str, self.font_name, self.font_size)
        c.drawString(self.width - page_width, 4, page_str)

        # Draw dot leaders between
        name_width = c.stringWidth(self.section_name + "  ", self.font_name, self.font_size)
        dot_width = c.stringWidth(". ", self.font_name, self.font_size)
        dot_start = name_width
        dot_end = self.width - page_width - 10

        x = dot_start
        while x < dot_end:
            c.drawString(x, 4, ".")
            x += dot_width


# ---------------------------------------------------------------------------
# NumberedCanvas — deferred footer rendering
# ---------------------------------------------------------------------------

class NumberedCanvas(canvas.Canvas):
    """Custom canvas that defers footer drawing until total page count is known."""

    def __init__(self, *args, **kwargs):
        self._footer_data = kwargs.pop("footer_data", {})
        self._font_map = kwargs.pop("font_map", {})
        self._skip_footer_pages = kwargs.pop("skip_footer_pages", {1})  # page 1 = cover
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_content_pages = len(self._saved_page_states) - 1  # exclude cover page
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            page_num = i + 1
            if page_num not in self._skip_footer_pages:
                self._draw_footer(page_num - 1, total_content_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_footer(self, content_page_num: int, total_content_pages: int):
        """Draw footer at bottom of page."""
        company = self._footer_data.get("company_name", "Company")
        year = self._footer_data.get("year", str(datetime.now().year))
        solution = self._footer_data.get("solution_name", "Solution")
        client = self._footer_data.get("client_name", "Client")

        footer_text = (
            f"\u00a9 {company} {year}  {solution} for {client}"
            f"    Page {content_page_num} of {total_content_pages}"
        )

        footer_font = self._font_map.get("CalibriLight", "Helvetica")
        self.setFillColor(FOOTER_TEXT_COLOR)
        self.setFont(footer_font, 10)
        self.drawString(MARGIN_LEFT, 30, footer_text)


# ---------------------------------------------------------------------------
# Style Factory
# ---------------------------------------------------------------------------

def create_styles(font_map: dict[str, str]) -> dict[str, ParagraphStyle]:
    """Create all paragraph styles using the resolved font map."""
    tnr = font_map.get("TimesNewRoman", "Times-Roman")
    tnr_bold = font_map.get("TimesNewRomanBold", "Times-Bold")
    tnr_italic = font_map.get("TimesNewRomanItalic", "Times-Italic")
    calibri = font_map.get("CalibriLight", "Helvetica")

    return {
        "body": ParagraphStyle(
            name="Body",
            fontName=tnr,
            fontSize=12,
            leading=16,
            textColor=BODY_TEXT_COLOR,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "body_bold": ParagraphStyle(
            name="BodyBold",
            fontName=tnr_bold,
            fontSize=12,
            leading=16,
            textColor=BODY_TEXT_COLOR,
            spaceAfter=4,
        ),
        "body_italic": ParagraphStyle(
            name="BodyItalic",
            fontName=tnr_italic,
            fontSize=12,
            leading=16,
            textColor=BODY_TEXT_COLOR,
            spaceAfter=4,
        ),
        "dash_bullet": ParagraphStyle(
            name="DashBullet",
            fontName=tnr,
            fontSize=12,
            leading=16,
            textColor=BODY_TEXT_COLOR,
            leftIndent=24,
            bulletIndent=10,
            spaceAfter=3,
        ),
        "round_bullet": ParagraphStyle(
            name="RoundBullet",
            fontName=tnr,
            fontSize=12,
            leading=16,
            textColor=BODY_TEXT_COLOR,
            leftIndent=24,
            bulletIndent=10,
            spaceAfter=3,
        ),
        "numbered": ParagraphStyle(
            name="Numbered",
            fontName=tnr,
            fontSize=12,
            leading=16,
            textColor=BODY_TEXT_COLOR,
            leftIndent=24,
            bulletIndent=10,
            spaceAfter=3,
        ),
        "contact_label": ParagraphStyle(
            name="ContactLabel",
            fontName=calibri,
            fontSize=11,
            leading=14,
            textColor=BODY_TEXT_COLOR,
        ),
        "contact_value": ParagraphStyle(
            name="ContactValue",
            fontName=calibri,
            fontSize=10,
            leading=13,
            textColor=BODY_TEXT_COLOR,
        ),
        "hyperlink": ParagraphStyle(
            name="Hyperlink",
            fontName=tnr,
            fontSize=12,
            leading=16,
            textColor=LINK_COLOR,
        ),
        "toc_entry": ParagraphStyle(
            name="TOCEntry",
            fontName=tnr,
            fontSize=12,
            leading=18,
            textColor=BODY_TEXT_COLOR,
        ),
        "sub_heading": ParagraphStyle(
            name="SubHeading",
            fontName=calibri,
            fontSize=14,
            leading=18,
            textColor=HEADING_BAR_COLOR,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "copyright": ParagraphStyle(
            name="Copyright",
            fontName=calibri,
            fontSize=10,
            leading=13,
            textColor=BODY_TEXT_COLOR,
            alignment=TA_LEFT,
        ),
        "table_header": ParagraphStyle(
            name="TableHeader",
            fontName=tnr_bold,
            fontSize=11,
            leading=14,
            textColor=BODY_TEXT_COLOR,
            alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            name="TableCell",
            fontName=tnr,
            fontSize=10,
            leading=13,
            textColor=BODY_TEXT_COLOR,
            alignment=TA_LEFT,
        ),
        "prepared_for": ParagraphStyle(
            name="PreparedFor",
            fontName=calibri,
            fontSize=12,
            leading=16,
            textColor=BODY_TEXT_COLOR,
        ),
    }


# ---------------------------------------------------------------------------
# RFI Document Builder
# ---------------------------------------------------------------------------

class RFIDocumentBuilder:
    """Builds the complete RFI response PDF using a two-pass approach."""

    def __init__(self, font_map: dict[str, str]):
        self.font_map = font_map
        self.styles = create_styles(font_map)
        self.total_pages = 0
        # Section tracking for TOC
        self._section_pages: dict[str, int] = {}

    def build(self, data: dict, output_path: str) -> str:
        """Build the PDF document.

        Uses a two-pass approach:
        - Pass 1: Render to determine total pages and section positions
        - Pass 2: Re-render with correct TOC page numbers
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Pass 1: Render to discover page counts
        import io
        buf = io.BytesIO()
        self._render(data, buf, pass_number=1)
        buf.seek(0)

        # Pass 2: Render with known TOC data
        self._render(data, output_path, pass_number=2)

        return output_path

    def _render(self, data: dict, output, pass_number: int):
        """Render the complete document."""
        footer_data = {
            "company_name": data.get("company", {}).get("name", "Company"),
            "year": data.get("copyright", {}).get("year", str(datetime.now().year)),
            "solution_name": data.get("solution_name", "Solution"),
            "client_name": data.get("client_name", "Client"),
        }

        # Build story (list of flowables)
        story = []

        # Page 1: Cover
        cover_page = data.get("cover_page", {})
        bg_color = HexColor(cover_page.get("background_color", "#1B3A5C"))
        bg_image = cover_page.get("background_image_path")
        story.append(CoverPageFlowable(data, self.font_map, bg_color, bg_image))
        story.append(NextPageTemplate("content"))
        story.append(PageBreak())

        # Page 2: Contact & Revision History
        story.extend(self._build_contact_revision(data))
        story.append(PageBreak())

        # Page 3: Table of Contents
        story.extend(self._build_toc(data, pass_number))
        story.append(PageBreak())

        # Page 4+: Executive Summary
        story.extend(self._build_executive_summary(data))
        story.append(PageBreak())

        # Company Profile & Credentials
        story.extend(self._build_company_profile(data))
        story.append(PageBreak())

        # Solution Profile
        story.extend(self._build_solution_profile(data))
        story.append(PageBreak())

        # Technical Information
        story.extend(self._build_technical_info(data))
        story.append(PageBreak())

        # Appendices & Copyright
        story.extend(self._build_appendices_copyright(data))

        # Create document
        heading_font = self.font_map.get("CalibriLight", "Helvetica")

        # Define page templates
        cover_frame = Frame(
            0, 0, PAGE_WIDTH, PAGE_HEIGHT,
            leftPadding=0, rightPadding=0,
            topPadding=0, bottomPadding=0,
            id="cover",
        )
        content_frame = Frame(
            MARGIN_LEFT, MARGIN_BOTTOM + 20,
            CONTENT_WIDTH, PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - 20,
            leftPadding=0, rightPadding=0,
            topPadding=0, bottomPadding=0,
            id="content",
        )

        cover_template = PageTemplate(id="cover", frames=[cover_frame])
        content_template = PageTemplate(id="content", frames=[content_frame])

        class _DocTemplate(BaseDocTemplate):
            """Custom doc template that tracks page numbers for sections."""
            def __init__(self, *args, section_tracker=None, **kwargs):
                self._section_tracker = section_tracker or {}
                super().__init__(*args, **kwargs)

            def afterFlowable(self, flowable):
                if isinstance(flowable, HeadingBarFlowable):
                    # Track which page this heading lands on
                    page_num = self.page
                    self._section_tracker[flowable.text] = page_num

        doc = _DocTemplate(
            output,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            section_tracker=self._section_pages,
        )
        doc.addPageTemplates([cover_template, content_template])

        # Build with NumberedCanvas for deferred footer
        def canvas_maker(filename, *args, **kwargs):
            return NumberedCanvas(
                filename, *args,
                footer_data=footer_data,
                font_map=self.font_map,
                skip_footer_pages={1},
                **kwargs,
            )

        doc.build(story, canvasmaker=canvas_maker)

        if pass_number == 1:
            self.total_pages = doc.page

    def _make_heading_bar(self, text: str, section_num: Optional[int] = None) -> HeadingBarFlowable:
        """Create a heading bar flowable."""
        heading_font = self.font_map.get("CalibriLight", "Helvetica")
        display_text = f"{section_num}  {text}" if section_num else text
        return HeadingBarFlowable(display_text, font_name=heading_font)

    def _make_styled_table(self, headers: list[str], rows: list[list[str]],
                           col_widths: Optional[list[float]] = None) -> Table:
        """Create a styled table with gray header row."""
        s = self.styles
        # Build table data with Paragraph objects for wrapping
        table_data = [[Paragraph(h, s["table_header"]) for h in headers]]
        for row in rows:
            table_data.append([Paragraph(str(cell), s["table_cell"]) for cell in row])

        if not col_widths:
            col_widths = [CONTENT_WIDTH / len(headers)] * len(headers)

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), self.font_map.get("TimesNewRomanBold", "Times-Bold")),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            # Alignment and padding
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            # Alternating row colors (light)
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F5F5F5")]),
        ]))
        return t

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_contact_revision(self, data: dict) -> list:
        """Build contact information and revision history page."""
        s = self.styles
        flowables = []

        # Prepared for line
        prepared_for = data.get("prepared_for", "")
        if prepared_for:
            flowables.append(Paragraph(f"Prepared for: <b>{prepared_for}</b>", s["prepared_for"]))
            flowables.append(Spacer(1, 8))

        date_prepared = data.get("date_prepared", "")
        if date_prepared:
            flowables.append(Paragraph(f"Date Prepared: {date_prepared}", s["prepared_for"]))
            flowables.append(Spacer(1, 16))

        # Contact Information heading bar
        flowables.append(self._make_heading_bar("Contact Information"))
        flowables.append(Spacer(1, 10))

        # Contact table
        company = data.get("company", {})
        contact_rows = []
        if company.get("name"):
            contact_rows.append(["Company", company["name"]])
        addr_parts = []
        if company.get("address_line1"):
            addr_parts.append(company["address_line1"])
        if company.get("address_line2"):
            addr_parts.append(company["address_line2"])
        if addr_parts:
            contact_rows.append(["Address", ", ".join(addr_parts)])
        if company.get("contact_name"):
            title = f" ({company['contact_title']})" if company.get("contact_title") else ""
            contact_rows.append(["Contact Person", f"{company['contact_name']}{title}"])
        if company.get("contact_phone"):
            contact_rows.append(["Phone", company["contact_phone"]])
        if company.get("contact_email"):
            contact_rows.append(["Email", company["contact_email"]])
        if company.get("website"):
            contact_rows.append(["Website", company["website"]])

        if contact_rows:
            table_data = []
            for row in contact_rows:
                table_data.append([
                    Paragraph(row[0], s["table_header"]),
                    Paragraph(row[1], s["table_cell"]),
                ])
            ct = Table(table_data, colWidths=[120, CONTENT_WIDTH - 120])
            ct.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (0, -1), HexColor("#F0F0F0")),
            ]))
            flowables.append(ct)

        flowables.append(Spacer(1, 24))

        # Revision History heading bar
        flowables.append(self._make_heading_bar("Revision History"))
        flowables.append(Spacer(1, 10))

        revisions = data.get("revision_history", [])
        if revisions:
            rev_headers = ["Rev.", "Date", "Author(s)", "Approver(s)", "Description"]
            rev_rows = []
            for rev in revisions:
                rev_rows.append([
                    rev.get("version", ""),
                    rev.get("date", ""),
                    rev.get("author", ""),
                    rev.get("approver", ""),
                    rev.get("description", ""),
                ])
            rev_table = self._make_styled_table(
                rev_headers, rev_rows,
                col_widths=[40, 65, 110, 140, 96],
            )
            flowables.append(rev_table)

        return flowables

    def _build_toc(self, data: dict, pass_number: int) -> list:
        """Build table of contents page."""
        flowables = []

        flowables.append(self._make_heading_bar("Table of Contents"))
        flowables.append(Spacer(1, 16))

        # Define TOC sections in order
        toc_sections = [
            ("Revision History", "Contact Information"),
            ("Table of Contents", "Table of Contents"),
            ("Executive Summary", "Executive Summary"),
            ("1  Company Profile & Credentials", "1  Company Profile & Credentials"),
            ("2  Solution Profile", "2  Solution Profile"),
            ("3  Technical Information", "3  Technical Information"),
            ("Appendices", "Appendices"),
            ("Copyright", "Copyright"),
        ]

        tnr = self.font_map.get("TimesNewRoman", "Times-Roman")

        if pass_number == 2 and self._section_pages:
            # Use actual page numbers from pass 1
            for display_name, tracker_key in toc_sections:
                page = self._section_pages.get(tracker_key, 0)
                if page > 0:
                    # Subtract 1 because cover is page 1 but content starts at "page 1"
                    flowables.append(TOCEntryFlowable(display_name, page - 1, font_name=tnr))
        else:
            # Pass 1 or no data - placeholder page numbers
            placeholder_pages = [1, 2, 3, 4, 5, 6, 7, 7]
            for (display_name, _), pnum in zip(toc_sections, placeholder_pages):
                flowables.append(TOCEntryFlowable(display_name, pnum, font_name=tnr))

        return flowables

    def _build_executive_summary(self, data: dict) -> list:
        """Build executive summary section."""
        s = self.styles
        flowables = []

        flowables.append(self._make_heading_bar("Executive Summary"))
        flowables.append(Spacer(1, 12))

        section = data.get("sections", {}).get("executive_summary", {})

        # Paragraphs
        for para_text in section.get("paragraphs", []):
            flowables.append(Paragraph(para_text, s["body"]))
            flowables.append(Spacer(1, 4))

        # Bullet points
        bullets = section.get("bullet_points", [])
        if bullets:
            flowables.append(Spacer(1, 6))
            for bullet in bullets:
                flowables.append(
                    Paragraph(f"- {bullet}", s["dash_bullet"])
                )

        return flowables

    def _build_company_profile(self, data: dict) -> list:
        """Build company profile and credentials section."""
        s = self.styles
        flowables = []

        flowables.append(self._make_heading_bar("Company Profile & Credentials", section_num=1))
        flowables.append(Spacer(1, 12))

        section = data.get("sections", {}).get("company_profile", {})

        # Description
        desc = section.get("description", "")
        if desc:
            flowables.append(Paragraph(desc, s["body"]))
            flowables.append(Spacer(1, 8))

        # Credentials
        creds = section.get("credentials", [])
        if creds:
            flowables.append(Paragraph("<b>Awards & Recognition:</b>", s["body_bold"]))
            flowables.append(Spacer(1, 4))
            for cred in creds:
                flowables.append(
                    Paragraph(f"\u2022 {cred}", s["round_bullet"])
                )
            flowables.append(Spacer(1, 8))

        # Certifications / analyst recognition
        certs = section.get("certifications", [])
        if certs:
            flowables.append(Paragraph("<b>Analyst Recognition:</b>", s["body_bold"]))
            flowables.append(Spacer(1, 4))
            for cert in certs:
                flowables.append(
                    Paragraph(f"\u2022 <i>{cert}</i>", s["round_bullet"])
                )
            flowables.append(Spacer(1, 8))

        # Experience highlights
        exp = section.get("experience_highlights", [])
        if exp:
            flowables.append(Paragraph("<b>Key Experience:</b>", s["body_bold"]))
            flowables.append(Spacer(1, 4))
            for item in exp:
                flowables.append(
                    Paragraph(f"- {item}", s["dash_bullet"])
                )
            flowables.append(Spacer(1, 8))

        # Hyperlinks
        links = section.get("hyperlinks", [])
        for link in links:
            flowables.append(
                Paragraph(
                    f'<a href="{link["url"]}" color="#0462c1">{link["text"]}</a>',
                    s["hyperlink"],
                )
            )

        return flowables

    def _build_solution_profile(self, data: dict) -> list:
        """Build solution/product profile section."""
        s = self.styles
        flowables = []

        flowables.append(self._make_heading_bar("Solution Profile", section_num=2))
        flowables.append(Spacer(1, 12))

        section = data.get("sections", {}).get("solution_profile", {})

        # Overview
        overview = section.get("overview", "")
        if overview:
            flowables.append(Paragraph(overview, s["body"]))
            flowables.append(Spacer(1, 10))

        # Features
        features = section.get("features", [])
        if features:
            flowables.append(Paragraph("<b>Key Features:</b>", s["body_bold"]))
            flowables.append(Spacer(1, 6))

            for feature in features:
                name = feature.get("name", "")
                desc = feature.get("description", "")
                flowables.append(
                    Paragraph(f"- <b>{name}:</b> {desc}", s["dash_bullet"])
                )
                flowables.append(Spacer(1, 2))

        return flowables

    def _build_technical_info(self, data: dict) -> list:
        """Build technical information section."""
        s = self.styles
        flowables = []

        flowables.append(self._make_heading_bar("Technical Information", section_num=3))
        flowables.append(Spacer(1, 12))

        section = data.get("sections", {}).get("technical_information", {})

        content = section.get("content", "")
        if content:
            flowables.append(Paragraph(content, s["body"]))
            flowables.append(Spacer(1, 10))

        # Attached documents
        attached = section.get("attached_documents", [])
        if attached:
            flowables.append(Paragraph("<b>Attached Documents:</b>", s["body_bold"]))
            flowables.append(Spacer(1, 4))
            for doc_name in attached:
                flowables.append(
                    Paragraph(f"- {doc_name}", s["dash_bullet"])
                )

        return flowables

    def _build_appendices_copyright(self, data: dict) -> list:
        """Build appendices list and copyright notice."""
        s = self.styles
        flowables = []

        # Appendices heading
        flowables.append(self._make_heading_bar("Appendices"))
        flowables.append(Spacer(1, 12))

        appendices = data.get("appendices", [])
        if appendices:
            for app in appendices:
                label = app.get("label", "")
                filename = app.get("filename", "")
                desc = app.get("description", "")
                line = f"- <b>{label}:</b> {filename}"
                if desc:
                    line += f" ({desc})"
                flowables.append(Paragraph(line, s["dash_bullet"]))
                flowables.append(Spacer(1, 2))
        else:
            flowables.append(Paragraph("No appendices.", s["body"]))

        flowables.append(Spacer(1, 30))

        # Copyright heading
        flowables.append(self._make_heading_bar("Copyright"))
        flowables.append(Spacer(1, 12))

        copyright_data = data.get("copyright", {})
        year = copyright_data.get("year", str(datetime.now().year))
        company_name = copyright_data.get("company_name", data.get("company", {}).get("name", ""))
        notice = copyright_data.get("notice_text", "")

        if notice:
            flowables.append(Paragraph(notice, s["copyright"]))
        else:
            flowables.append(
                Paragraph(
                    f"\u00a9 {year} {company_name}. All rights reserved.",
                    s["copyright"],
                )
            )

        return flowables


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a professional RFI Response PDF document",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python3 generate_pdf.py --input data.json --output response.pdf --verbose
        """,
    )
    parser.add_argument("--input", required=True, help="Path to JSON data file")
    parser.add_argument("--output", required=True, help="Output PDF file path")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Load JSON data
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    # Register fonts
    print("Discovering and registering fonts...")
    font_mgr = FontManager()
    font_map = font_mgr.register_fonts()

    if font_mgr.substitutions:
        print("Font substitutions:")
        for original, substitute in font_mgr.substitutions.items():
            print(f"  {original} -> {substitute}")
    else:
        print("All fonts found and registered successfully.")

    # Build PDF
    print(f"Generating PDF: {args.output}")
    builder = RFIDocumentBuilder(font_map)
    try:
        output_path = builder.build(data, args.output)
        print(f"\nPDF generated successfully!")
        print(f"  Output: {output_path}")
        print(f"  Pages: {builder.total_pages}")
    except Exception as e:
        print(f"Error generating PDF: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
