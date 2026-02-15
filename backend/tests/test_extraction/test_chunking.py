import pytest
from app.extraction.chunking import chunk_document, estimate_tokens


class TestChunking:
    def test_short_text_single_chunk(self):
        text = "This is a short text."
        chunks = chunk_document(text, max_tokens=1000)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text
        assert chunks[0]["chunk_index"] == 0

    def test_long_text_multiple_chunks(self):
        # Create text that's ~2000 tokens (8000 chars)
        text = "This is a sample sentence for testing. " * 250
        chunks = chunk_document(text, max_tokens=500, overlap_tokens=50)
        assert len(chunks) > 1
        # Verify chunk indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_chunk_overlap(self):
        text = "Paragraph one content here.\n\nParagraph two content here.\n\nParagraph three content here."
        # Force small chunks
        chunks = chunk_document(text, max_tokens=20, overlap_tokens=5)
        if len(chunks) > 1:
            # There should be some overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                assert chunks[i]["end_char"] > chunks[i + 1]["start_char"] or \
                       chunks[i + 1]["start_char"] < chunks[i]["end_char"]

    def test_estimate_tokens(self):
        text = "Hello world"  # 11 chars
        tokens = estimate_tokens(text)
        assert tokens == 2  # 11 // 4

    def test_empty_text(self):
        chunks = chunk_document("")
        assert len(chunks) == 1
        assert chunks[0]["text"] == ""

    def test_chunk_metadata(self):
        text = "Some text content"
        chunks = chunk_document(text)
        assert "start_char" in chunks[0]
        assert "end_char" in chunks[0]
        assert "chunk_index" in chunks[0]
        assert "text" in chunks[0]
