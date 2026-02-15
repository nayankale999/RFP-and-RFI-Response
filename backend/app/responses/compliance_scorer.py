import logging

from app.shared.ai_client import get_ai_client

logger = logging.getLogger(__name__)

COMPLIANCE_TOOL = {
    "name": "score_compliance",
    "description": "Score overall compliance of responses against requirements",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Overall compliance score (0-100)",
            },
            "functional_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "non_functional_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "risk_areas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "area": {"type": "string"},
                        "risk_level": {"type": "string", "enum": ["high", "medium", "low"]},
                        "description": {"type": "string"},
                    },
                    "required": ["area", "risk_level", "description"],
                },
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["overall_score", "risk_areas"],
    },
}


def calculate_compliance_scores(requirements: list[dict], responses: list[dict]) -> dict:
    """Calculate compliance scores from requirement-response pairs."""
    if not responses:
        return {"overall_score": 0, "functional_score": 0, "non_functional_score": 0}

    status_weights = {
        "fully_compliant": 1.0,
        "configurable": 0.8,
        "partially_compliant": 0.5,
        "custom_dev": 0.3,
        "not_applicable": None,  # excluded from scoring
    }

    # Build response lookup
    resp_by_req = {str(r.get("requirement_id")): r for r in responses}

    scores_by_type = {}
    for req in requirements:
        req_id = str(req.get("id"))
        resp = resp_by_req.get(req_id)
        if not resp:
            continue

        status = resp.get("compliance_status", "custom_dev")
        weight = status_weights.get(status)
        if weight is None:
            continue

        req_type = req.get("type", "functional")
        if req_type not in scores_by_type:
            scores_by_type[req_type] = []
        scores_by_type[req_type].append(weight)

    # Calculate per-type scores
    type_scores = {}
    for req_type, weights in scores_by_type.items():
        type_scores[req_type] = (sum(weights) / len(weights) * 100) if weights else 0

    # Overall score
    all_weights = [w for ws in scores_by_type.values() for w in ws]
    overall = (sum(all_weights) / len(all_weights) * 100) if all_weights else 0

    return {
        "overall_score": round(overall, 1),
        "functional_score": round(type_scores.get("functional", 0), 1),
        "non_functional_score": round(type_scores.get("non_functional", 0), 1),
        "commercial_score": round(type_scores.get("commercial", 0), 1),
        "technical_score": round(type_scores.get("technical", 0), 1),
        "scores_by_type": {k: round(v, 1) for k, v in type_scores.items()},
        "total_requirements": len(requirements),
        "total_responses": len(responses),
        "status_breakdown": _count_statuses(responses),
    }


def _count_statuses(responses: list[dict]) -> dict[str, int]:
    counts = {}
    for r in responses:
        status = r.get("compliance_status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts
