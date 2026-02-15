import logging
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import KnowledgeBase
from app.shared.ai_client import get_ai_client
from app.shared.embedding_client import get_embedding_client
from app.shared.exceptions import ResponseGenerationError

logger = logging.getLogger(__name__)

RESPONSE_GENERATION_TOOL = {
    "name": "generate_response",
    "description": "Generate a structured response to an RFP requirement",
    "input_schema": {
        "type": "object",
        "properties": {
            "compliance_status": {
                "type": "string",
                "enum": ["fully_compliant", "partially_compliant", "configurable", "custom_dev", "not_applicable"],
                "description": "How compliant the solution is with this requirement",
            },
            "response_text": {
                "type": "string",
                "description": "Detailed response to the requirement (2-5 sentences)",
            },
            "confidence_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confidence in the response accuracy (0-1)",
            },
            "key_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key product features that address this requirement",
            },
            "notes": {
                "type": "string",
                "description": "Internal notes for the proposal team",
            },
        },
        "required": ["compliance_status", "response_text", "confidence_score"],
    },
}

SYSTEM_PROMPT = """You are an expert proposal writer generating responses for RFP/RFI requirements.

Your task is to generate professional, accurate responses based on:
1. The requirement description
2. Relevant product capabilities from the knowledge base
3. Past successful responses to similar requirements

Guidelines:
- Be specific and professional
- Reference concrete capabilities, not vague promises
- If knowledge base entries are provided, ground your response in them
- Set compliance_status accurately:
  - fully_compliant: The solution natively meets this requirement
  - partially_compliant: The solution meets most but not all aspects
  - configurable: The solution can meet this through configuration
  - custom_dev: Custom development would be needed
  - not_applicable: The requirement doesn't apply
- Set confidence_score honestly (0-1):
  - >0.8: Strong knowledge base match, high confidence
  - 0.5-0.8: Partial match, reasonable confidence
  - <0.5: Low confidence, needs human review
- Keep responses professional and concise (2-5 sentences)"""


async def generate_response(
    requirement: dict[str, Any],
    db: AsyncSession,
    org_id: str | None = None,
) -> dict[str, Any]:
    """Generate a response for a single requirement using RAG."""
    ai = get_ai_client()
    embedding_client = get_embedding_client()

    # 1. Embed the requirement for similarity search
    req_text = f"{requirement.get('title', '')} {requirement.get('description', '')}"
    query_embedding = embedding_client.embed_query(req_text)

    # 2. Search knowledge base for relevant entries
    kb_context = await _search_knowledge_base(db, query_embedding, org_id, top_k=5)

    # 3. Build context for the LLM
    context_parts = []
    source_refs = []
    if kb_context:
        context_parts.append("=== Relevant Product Capabilities & Past Responses ===")
        for i, entry in enumerate(kb_context):
            context_parts.append(f"\n--- Reference {i+1}: {entry['title']} ---")
            context_parts.append(entry["content"][:500])
            source_refs.append({"id": str(entry["id"]), "title": entry["title"]})

    context_str = "\n".join(context_parts) if context_parts else "No relevant knowledge base entries found."

    # 4. Generate response
    user_prompt = f"""Generate a response for this RFP requirement:

Requirement ID: {requirement.get('req_number', 'N/A')}
Title: {requirement.get('title', 'N/A')}
Description: {requirement.get('description', 'N/A')}
Type: {requirement.get('type', 'N/A')}
Category: {requirement.get('category', 'N/A')}
Mandatory: {requirement.get('is_mandatory', True)}

{context_str}

Generate a professional, grounded response."""

    try:
        result = ai.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            tools=[RESPONSE_GENERATION_TOOL],
            tool_choice={"type": "tool", "name": "generate_response"},
            max_tokens=1024,
        )

        result["source_refs"] = source_refs
        result["is_ai_generated"] = True

        logger.info(
            f"Generated response for {requirement.get('req_number', '?')}: "
            f"status={result.get('compliance_status')}, confidence={result.get('confidence_score')}"
        )
        return result

    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        raise ResponseGenerationError(f"Failed to generate response: {e}")


async def generate_responses_batch(
    requirements: list[dict[str, Any]],
    db: AsyncSession,
    org_id: str | None = None,
) -> list[dict[str, Any]]:
    """Generate responses for multiple requirements."""
    responses = []
    for req in requirements:
        try:
            resp = await generate_response(req, db, org_id)
            resp["requirement_id"] = req.get("id")
            responses.append(resp)
        except Exception as e:
            logger.warning(f"Failed to generate response for {req.get('req_number')}: {e}")
            responses.append({
                "requirement_id": req.get("id"),
                "compliance_status": "custom_dev",
                "response_text": "Response generation failed. Manual response required.",
                "confidence_score": 0.0,
                "is_ai_generated": True,
                "notes": f"Error: {str(e)}",
            })
    return responses


async def _search_knowledge_base(
    db: AsyncSession,
    query_embedding: list[float],
    org_id: str | None,
    top_k: int = 5,
) -> list[dict]:
    """Search the knowledge base using vector similarity."""
    try:
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        query = text("""
            SELECT id, title, content, category,
                   1 - (embedding <=> :embedding::vector) as similarity
            FROM knowledge_base
            WHERE embedding IS NOT NULL
            AND (:org_id IS NULL OR org_id = :org_id)
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """)

        result = await db.execute(
            query,
            {"embedding": embedding_str, "org_id": org_id, "top_k": top_k},
        )
        rows = result.mappings().all()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "category": row["category"],
                "similarity": row["similarity"],
            }
            for row in rows
            if row["similarity"] > 0.3  # minimum relevance threshold
        ]

    except Exception as e:
        logger.warning(f"Knowledge base search failed: {e}")
        return []
