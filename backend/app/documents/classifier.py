import logging

from app.shared.ai_client import get_ai_client
from app.shared.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)

DOCUMENT_CATEGORIES = [
    "rfp_document",
    "commercial_terms",
    "tech_requirements",
    "pricing_sheet",
    "legal_appendix",
    "evaluation_criteria",
]

CATEGORY_DESCRIPTIONS = {
    "rfp_document": "Main RFP/RFI document containing scope, background, and general requirements",
    "commercial_terms": "Commercial terms, payment conditions, and business requirements",
    "tech_requirements": "Technical requirement matrices, architecture specs, integration requirements",
    "pricing_sheet": "Pricing templates, cost breakdowns, rate cards, financial tables",
    "legal_appendix": "Legal terms, compliance requirements, contractual clauses, NDAs",
    "evaluation_criteria": "Scoring criteria, evaluation methodology, weighting factors",
}


def classify_document(text: str, filename: str, tables_present: bool = False) -> str:
    """Classify a document into one of the predefined categories using Claude."""
    ai = get_ai_client()

    categories_desc = "\n".join(
        f"- {cat}: {desc}" for cat, desc in CATEGORY_DESCRIPTIONS.items()
    )

    system_prompt = """You are an expert document classifier for RFP/RFI documents.
Classify the given document into exactly one category. Respond with ONLY the category name."""

    user_prompt = f"""Classify this document into one of these categories:
{categories_desc}

Filename: {filename}
Has tables: {tables_present}

Document text (first 3000 chars):
{text[:3000]}

Category:"""

    try:
        result = ai.classify(text[:3000], DOCUMENT_CATEGORIES, context=f"Filename: {filename}")
        logger.info(f"Classified {filename} as: {result}")
        return result
    except Exception as e:
        logger.error(f"Classification failed for {filename}: {e}")
        # Fallback: use heuristics
        return _heuristic_classify(text, filename, tables_present)


def _heuristic_classify(text: str, filename: str, tables_present: bool) -> str:
    """Fallback classification using keyword heuristics."""
    text_lower = text.lower()
    filename_lower = filename.lower()

    # Check filename patterns
    if any(w in filename_lower for w in ["price", "pricing", "cost", "rate", "commercial"]):
        return "pricing_sheet"
    if any(w in filename_lower for w in ["legal", "contract", "terms", "nda", "compliance"]):
        return "legal_appendix"
    if any(w in filename_lower for w in ["eval", "criteria", "scoring", "weight"]):
        return "evaluation_criteria"
    if any(w in filename_lower for w in ["tech", "architecture", "integration", "spec"]):
        return "tech_requirements"

    # Check content patterns
    pricing_keywords = ["unit price", "total cost", "license fee", "per user", "annual cost"]
    if sum(1 for kw in pricing_keywords if kw in text_lower) >= 2:
        return "pricing_sheet"

    legal_keywords = ["indemnification", "liability", "termination", "governing law", "warranty"]
    if sum(1 for kw in legal_keywords if kw in text_lower) >= 2:
        return "legal_appendix"

    eval_keywords = ["evaluation criteria", "scoring", "weightage", "selection criteria"]
    if sum(1 for kw in eval_keywords if kw in text_lower) >= 2:
        return "evaluation_criteria"

    tech_keywords = ["api", "integration", "architecture", "database", "infrastructure"]
    if sum(1 for kw in tech_keywords if kw in text_lower) >= 3:
        return "tech_requirements"

    return "rfp_document"
