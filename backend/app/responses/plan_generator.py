import logging
from typing import Any

from app.shared.ai_client import get_ai_client
from app.shared.exceptions import ResponseGenerationError

logger = logging.getLogger(__name__)

PLAN_GENERATION_TOOL = {
    "name": "generate_response_plan",
    "description": "Generate an internal RFP response plan with workstreams and assignments",
    "input_schema": {
        "type": "object",
        "properties": {
            "workstreams": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Workstream name"},
                        "owner_role": {
                            "type": "string",
                            "description": "Recommended owner role (e.g., Product Team, Architecture, Finance, Legal)",
                        },
                        "description": {"type": "string"},
                        "estimated_effort_days": {"type": "integer"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Other workstream names this depends on",
                        },
                    },
                    "required": ["name", "owner_role", "description", "priority"],
                },
            },
            "escalation_matrix": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["L1", "L2", "L3"]},
                        "role": {"type": "string"},
                        "trigger": {"type": "string"},
                    },
                    "required": ["level", "role", "trigger"],
                },
            },
            "collaboration_notes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["workstreams"],
    },
}

SYSTEM_PROMPT = """You are an expert proposal manager creating an internal response plan for an RFP.

Based on the requirements summary, create:
1. Workstreams with clear ownership and priorities
2. An escalation matrix for blockers
3. Collaboration notes for the team

Standard workstreams include:
- Functional Responses (Product Team)
- Non-Functional / Architecture Responses (Architecture Team)
- Pricing & Commercial (Finance)
- Legal Review (Legal)
- Technical Writing & Assembly (Proposal Lead)
- Executive Summary (Senior Management)
- Solution Demo Preparation (Pre-Sales)

Adjust based on the actual requirements found in the RFP."""


def generate_response_plan(
    requirements_summary: dict[str, Any],
    schedule_events: list[dict],
    project_name: str,
) -> dict[str, Any]:
    """Generate an internal response plan based on extracted requirements and schedule."""
    ai = get_ai_client()

    # Build summary of requirements by type
    type_counts = requirements_summary.get("type_counts", {})
    total = requirements_summary.get("total", 0)

    # Find submission deadline
    deadline = "Not specified"
    for event in schedule_events:
        if event.get("event_type") == "submission_deadline":
            deadline = event.get("date", "Not specified")
            break

    user_prompt = f"""Create an internal response plan for this RFP:

Project: {project_name}
Submission Deadline: {deadline}
Total Requirements: {total}
Breakdown by type:
{chr(10).join(f'  - {t}: {c}' for t, c in type_counts.items())}

Key schedule events:
{chr(10).join(f'  - {e.get("event_name")}: {e.get("date", "TBD")}' for e in schedule_events[:10])}

Generate a comprehensive response plan with workstreams, escalation matrix, and collaboration notes."""

    try:
        result = ai.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            tools=[PLAN_GENERATION_TOOL],
            tool_choice={"type": "tool", "name": "generate_response_plan"},
            max_tokens=2048,
        )

        logger.info(f"Generated response plan with {len(result.get('workstreams', []))} workstreams")
        return result

    except Exception as e:
        logger.error(f"Plan generation failed: {e}")
        raise ResponseGenerationError(f"Plan generation failed: {e}")
