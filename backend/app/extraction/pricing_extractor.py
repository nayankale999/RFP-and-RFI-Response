import logging
from typing import Any

from app.shared.ai_client import get_ai_client
from app.shared.exceptions import ExtractionError

logger = logging.getLogger(__name__)

PRICING_EXTRACTION_TOOL = {
    "name": "extract_pricing_structure",
    "description": "Extract pricing structure and template from RFP/RFI documents",
    "input_schema": {
        "type": "object",
        "properties": {
            "has_pricing_template": {
                "type": "boolean",
                "description": "Whether the document contains a pricing template to fill",
            },
            "pricing_format": {
                "type": "string",
                "description": "Description of the expected pricing format",
            },
            "pricing_categories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["license", "implementation", "support", "add_on", "training", "hosting", "other"],
                        },
                        "line_item": {
                            "type": "string",
                            "description": "Specific line item or service",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of what needs to be priced",
                        },
                        "unit_of_measure": {
                            "type": "string",
                            "description": "E.g., per user, per month, per transaction, lump sum",
                        },
                        "multi_year": {
                            "type": "boolean",
                            "description": "Whether multi-year pricing is requested",
                        },
                        "years_requested": {
                            "type": "integer",
                            "description": "Number of years if multi-year pricing requested",
                        },
                    },
                    "required": ["category", "line_item", "description"],
                },
            },
            "currency": {
                "type": "string",
                "description": "Required currency for pricing",
            },
            "pricing_notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional pricing requirements or constraints",
            },
        },
        "required": ["has_pricing_template", "pricing_categories"],
    },
}

SYSTEM_PROMPT = """You are an expert at analyzing RFP/RFI pricing requirements.

Extract:
1. Whether a specific pricing template/format is required
2. All pricing categories and line items requested
3. Unit of measure for each item
4. Multi-year pricing requirements
5. Currency requirements
6. Any pricing constraints or special requirements (volume discounts, tax handling, etc.)

Be thorough in identifying all cost components the buyer expects."""


def extract_pricing_structure(text: str) -> dict[str, Any]:
    """Extract pricing structure and requirements from document text."""
    ai = get_ai_client()

    try:
        result = ai.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"""Analyze this document for pricing requirements and templates:

{text[:6000]}

Extract the complete pricing structure expected by the buyer.""",
            tools=[PRICING_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_pricing_structure"},
            max_tokens=2048,
        )

        logger.info(
            f"Extracted pricing structure: {len(result.get('pricing_categories', []))} categories, "
            f"template: {result.get('has_pricing_template', False)}"
        )
        return result

    except Exception as e:
        logger.error(f"Pricing extraction failed: {e}")
        raise ExtractionError(f"Pricing extraction failed: {e}")
