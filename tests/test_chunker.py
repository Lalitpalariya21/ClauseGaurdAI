"""
Pytest tests for ingestion/chunker.py

Covers:
- test_chunking_respects_size
- test_chunking_has_overlap_metadata
- test_get_full_text
- test_empty_pages_handled
"""

import pytest

from ingestion.chunker import chunk_pages, get_full_text


# ── Fixtures ───────────────────────────────────────────────────────────

def _make_pages(texts: list[str]) -> list[dict]:
    """Helper: build synthetic page dicts as returned by pdf_loader."""
    pages = []
    for i, text in enumerate(texts, start=1):
        pages.append({
            "page": i,
            "text": text,
            "char_count": len(text),
        })
    return pages


def _long_text(word: str = "word", n: int = 300) -> str:
    """Return a long text made of repeated words (suitable for chunking)."""
    return (" ".join([word] * n))


# ── Tests: chunk_pages ─────────────────────────────────────────────────

class TestChunkPages:
    def test_chunking_respects_size(self):
        """Each chunk's text length should not exceed chunk_size + overlap."""
        pages = _make_pages([_long_text("contract", 500)])
        chunk_size = 200
        overlap = 50
        chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=overlap)

        assert len(chunks) > 0
        for chunk in chunks:
            # Allow small tolerance for word-boundary splitting
            assert len(chunk["text"]) <= chunk_size + overlap + 50, (
                f"Chunk too large: {len(chunk['text'])} chars"
            )

    def test_chunking_has_overlap_metadata(self):
        """Every chunk dict must carry required metadata keys."""
        pages = _make_pages([_long_text("clause", 300)])
        chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=50)

        required_keys = {"chunk_id", "text", "page", "start_char", "end_char"}
        for chunk in chunks:
            missing = required_keys - chunk.keys()
            assert not missing, f"Chunk missing keys: {missing}"

    def test_chunk_ids_are_unique(self):
        """chunk_id values must be unique across the whole document."""
        pages = _make_pages([_long_text("term", 400), _long_text("bond", 400)])
        chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=50)
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Duplicate chunk_ids detected"

    def test_chunk_page_numbers_are_valid(self):
        """chunk['page'] must refer to an existing page number."""
        pages = _make_pages(["Page one text " * 50, "Page two text " * 50])
        valid_pages = {p["page"] for p in pages}
        chunks = chunk_pages(pages, chunk_size=150, chunk_overlap=30)
        for chunk in chunks:
            assert chunk["page"] in valid_pages

    def test_chunking_multiple_pages(self):
        """Chunks should be produced from all pages."""
        pages = _make_pages([
            _long_text("alpha", 100),
            _long_text("beta", 100),
            _long_text("gamma", 100),
        ])
        chunks = chunk_pages(pages, chunk_size=150, chunk_overlap=30)
        # We expect chunks from more than one page
        pages_in_chunks = {c["page"] for c in chunks}
        assert len(pages_in_chunks) >= 2

    def test_empty_pages_handled(self):
        """Pages with empty or whitespace-only text should be skipped gracefully."""
        pages = _make_pages(["", "   ", "\n\n", "Real contract content " * 20])
        # Should not raise
        chunks = chunk_pages(pages, chunk_size=150, chunk_overlap=30)
        assert isinstance(chunks, list)
        # Chunks should come from the non-empty page
        assert len(chunks) > 0

    def test_all_empty_pages_returns_empty_list(self):
        """If every page is empty, chunk_pages should return an empty list."""
        pages = _make_pages(["", "   ", "\t"])
        chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=50)
        assert chunks == []

    def test_single_short_page_produces_one_chunk(self):
        """A single page shorter than chunk_size should produce exactly one chunk."""
        short_text = "Short contract clause."
        pages = _make_pages([short_text])
        chunks = chunk_pages(pages, chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 1
        assert short_text in chunks[0]["text"]

    def test_overlap_text_appears_in_consecutive_chunks(self):
        """The end of chunk N should appear near the start of chunk N+1."""
        # Create a long predictable text
        words = [f"word{i}" for i in range(200)]
        text = " ".join(words)
        pages = _make_pages([text])
        chunk_size = 100
        overlap = 40
        chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=overlap)

        if len(chunks) >= 2:
            end_of_first = chunks[0]["text"][-overlap:]
            # At least some of the overlap text should appear in chunk 1 start
            assert any(
                word in chunks[1]["text"][:chunk_size]
                for word in end_of_first.split()
            )


# ── Tests: get_full_text ───────────────────────────────────────────────

class TestGetFullText:
    def test_get_full_text(self):
        """get_full_text should concatenate all page texts."""
        pages = _make_pages(["Hello world.", "Second page content."])
        full = get_full_text(pages)
        assert "Hello world." in full
        assert "Second page content." in full

    def test_get_full_text_preserves_order(self):
        """Pages should appear in ascending page-number order."""
        pages = _make_pages(["First", "Second", "Third"])
        full = get_full_text(pages)
        pos_first = full.index("First")
        pos_second = full.index("Second")
        pos_third = full.index("Third")
        assert pos_first < pos_second < pos_third

    def test_get_full_text_empty_pages(self):
        """get_full_text with all empty pages should return an empty / whitespace string."""
        pages = _make_pages(["", "   "])
        full = get_full_text(pages)
        assert full.strip() == ""

    def test_get_full_text_no_pages(self):
        """get_full_text with an empty list should return an empty string."""
        full = get_full_text([])
        assert full == "" or full.strip() == ""
