import re
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def chunk_document(text: str, max_tokens: int | None = None, overlap_tokens: int | None = None) -> list[dict]:
    """Split document text into chunks with overlap, respecting semantic boundaries.

    Returns list of dicts: [{text, start_char, end_char, chunk_index}]
    """
    settings = get_settings()
    max_tokens = max_tokens or settings.max_chunk_tokens
    overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens

    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    if estimate_tokens(text) <= max_tokens:
        return [{"text": text, "start_char": 0, "end_char": len(text), "chunk_index": 0}]

    # Find semantic boundaries (headings, double newlines, section breaks)
    boundary_pattern = re.compile(
        r"(?:\n\s*\n)"  # Double newline (paragraph break)
        r"|(?:\n#{1,6}\s)"  # Markdown headings
        r"|(?:\n\d+\.\s)"  # Numbered list items
        r"|(?:\n-{3,})"  # Horizontal rules
        r"|(?:\nSection\s+\d)"  # Section markers
        r"|(?:\n[A-Z][A-Z\s]{5,}\n)"  # ALL CAPS headings
    )

    boundaries = [0]
    for match in boundary_pattern.finditer(text):
        boundaries.append(match.start())
    boundaries.append(len(text))

    chunks = []
    chunk_start = 0
    chunk_index = 0

    while chunk_start < len(text):
        chunk_end = min(chunk_start + max_chars, len(text))

        # Try to end at a semantic boundary
        if chunk_end < len(text):
            best_boundary = chunk_start
            for b in boundaries:
                if chunk_start < b <= chunk_end:
                    best_boundary = b
            if best_boundary > chunk_start + (max_chars // 2):
                chunk_end = best_boundary

        chunk_text = text[chunk_start:chunk_end].strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "start_char": chunk_start,
                "end_char": chunk_end,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

        # Move forward with overlap
        chunk_start = chunk_end - overlap_chars
        if chunk_start >= len(text) or chunk_end >= len(text):
            break

    logger.info(f"Split document into {len(chunks)} chunks (max_tokens={max_tokens})")
    return chunks
