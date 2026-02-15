import logging
from typing import Any

from app.shared.ai_client import get_ai_client
from app.shared.exceptions import ExtractionError

logger = logging.getLogger(__name__)

SCHEDULE_EXTRACTION_TOOL = {
    "name": "extract_schedule",
    "description": "Extract schedule events and dates from RFP/RFI documents",
    "input_schema": {
        "type": "object",
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "event_type": {
                            "type": "string",
                            "enum": [
                                "rfp_release",
                                "clarification_window",
                                "qa_deadline",
                                "submission_deadline",
                                "demo_date",
                                "award_notification",
                                "contract_start",
                                "other",
                            ],
                        },
                        "event_name": {
                            "type": "string",
                            "description": "Human-readable event name",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format, or null if not specified",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes or context about this event",
                        },
                    },
                    "required": ["event_type", "event_name"],
                },
            },
        },
        "required": ["events"],
    },
}

SYSTEM_PROMPT = """You are an expert at extracting schedule information from RFP/RFI documents.

Extract all dates and timeline events. Look for:
- RFP issuance/release date
- Clarification or Q&A periods
- Question submission deadlines
- Proposal submission deadlines
- Vendor presentation/demo dates
- Award notification dates
- Contract execution dates
- Project start dates
- Any milestone dates

Convert all dates to YYYY-MM-DD format. If only a relative date is given (e.g., "within 30 days"),
note it in the notes field."""


def extract_schedule(text: str) -> list[dict[str, Any]]:
    """Extract schedule events and dates from document text."""
    ai = get_ai_client()

    # Use first ~8000 chars - schedules are usually near the beginning
    excerpt = text[:8000]

    try:
        result = ai.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"""Extract all schedule events and dates from this RFP/RFI document:

{excerpt}

Extract every date and timeline event you can find.""",
            tools=[SCHEDULE_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_schedule"},
            max_tokens=2048,
        )

        events = result.get("events", [])
        logger.info(f"Extracted {len(events)} schedule events")
        return events

    except Exception as e:
        logger.error(f"Schedule extraction failed: {e}")
        raise ExtractionError(f"Schedule extraction failed: {e}")
