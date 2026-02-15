import logging
from typing import Any

import numpy as np

from app.extraction.chunking import chunk_document
from app.shared.ai_client import get_ai_client
from app.shared.embedding_client import get_embedding_client
from app.shared.exceptions import ExtractionError

logger = logging.getLogger(__name__)

REQUIREMENT_EXTRACTION_TOOL = {
    "name": "extract_requirements",
    "description": "Extract structured requirements from RFP/RFI document text",
    "input_schema": {
        "type": "object",
        "properties": {
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title summarizing the requirement",
                        },
                        "description": {
                            "type": "string",
                            "description": "Full description of the requirement",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["functional", "non_functional", "commercial", "legal", "technical"],
                            "description": "Requirement type",
                        },
                        "category": {
                            "type": "string",
                            "description": "Sub-category (e.g., security, scalability, integration, compliance, UI, reporting)",
                        },
                        "is_mandatory": {
                            "type": "boolean",
                            "description": "Whether this is a mandatory or optional requirement",
                        },
                        "response_required": {
                            "type": "boolean",
                            "description": "Whether a response is required for this requirement",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Priority level",
                        },
                        "reference_section": {
                            "type": "string",
                            "description": "Section reference from the source document",
                        },
                    },
                    "required": ["title", "description", "type", "is_mandatory", "response_required"],
                },
            },
        },
        "required": ["requirements"],
    },
}

SYSTEM_PROMPT = """You are an expert RFP/RFI analyst. Your task is to extract ALL requirements from the given document text.

For each requirement, identify:
1. A clear, concise title
2. The full description
3. Whether it's functional, non-functional, commercial, legal, or technical
4. A sub-category (security, scalability, integration, compliance, UI, reporting, data, performance, availability, etc.)
5. Whether it's mandatory or optional
6. Whether a vendor response is required
7. Priority (high/medium/low)
8. The section reference

Be thorough - extract every explicit and implied requirement. Look for:
- "shall", "must", "should", "will" statements
- Numbered requirement lists
- Compliance matrices
- Technical specifications
- SLA requirements
- Security requirements
- Integration requirements
- Regulatory/legal obligations"""


def extract_requirements(text: str, document_id: str | None = None) -> list[dict[str, Any]]:
    """Extract requirements from document text using Claude structured outputs.

    For large documents, chunks the text and extracts from each chunk,
    then deduplicates using embedding similarity.
    """
    ai = get_ai_client()
    chunks = chunk_document(text)
    all_requirements = []

    for chunk in chunks:
        try:
            user_prompt = f"""Extract all requirements from this RFP/RFI document section:

{chunk['text']}

Extract every requirement you can find, even implied ones."""

            result = ai.generate_structured(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                tools=[REQUIREMENT_EXTRACTION_TOOL],
                tool_choice={"type": "tool", "name": "extract_requirements"},
                max_tokens=4096,
            )

            reqs = result.get("requirements", [])
            # Tag each requirement with chunk info
            for req in reqs:
                req["_chunk_index"] = chunk["chunk_index"]
                req["_start_char"] = chunk["start_char"]
            all_requirements.extend(reqs)

            logger.info(f"Extracted {len(reqs)} requirements from chunk {chunk['chunk_index']}")

        except Exception as e:
            logger.warning(f"Extraction failed for chunk {chunk['chunk_index']}: {e}")
            continue

    if not all_requirements:
        logger.warning("No requirements extracted from document")
        return []

    # Deduplicate across chunks using embedding similarity
    deduplicated = _deduplicate_requirements(all_requirements)

    # Assign requirement numbers
    counters = {"functional": 0, "non_functional": 0, "commercial": 0, "legal": 0, "technical": 0}
    prefixes = {"functional": "FR", "non_functional": "NFR", "commercial": "CR", "legal": "LR", "technical": "TR"}

    for req in deduplicated:
        req_type = req.get("type", "functional")
        counters[req_type] = counters.get(req_type, 0) + 1
        prefix = prefixes.get(req_type, "REQ")
        req["req_number"] = f"{prefix}-{counters[req_type]:03d}"

    logger.info(f"Final extracted requirements: {len(deduplicated)} (from {len(all_requirements)} raw)")
    return deduplicated


def _deduplicate_requirements(requirements: list[dict]) -> list[dict]:
    """Remove duplicate requirements using embedding similarity."""
    if len(requirements) <= 1:
        return requirements

    try:
        embedding_client = get_embedding_client()
        texts = [f"{r.get('title', '')} {r.get('description', '')}" for r in requirements]
        embeddings = embedding_client.embed_texts(texts)

        keep = [True] * len(requirements)
        threshold = 0.95  # cosine similarity threshold

        for i in range(len(requirements)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(requirements)):
                if not keep[j]:
                    continue
                sim = _cosine_similarity(embeddings[i], embeddings[j])
                if sim > threshold:
                    # Keep the one from the earlier chunk (likely more complete context)
                    keep[j] = False

        deduplicated = [req for req, k in zip(requirements, keep) if k]
        removed = len(requirements) - len(deduplicated)
        if removed:
            logger.info(f"Deduplicated: removed {removed} duplicate requirements")
        return deduplicated

    except Exception as e:
        logger.warning(f"Deduplication failed, returning all: {e}")
        return requirements


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
