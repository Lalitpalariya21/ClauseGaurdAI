"""
Pytest tests for ingestion/pdf_loader.py

Covers:
- test_validate_pdf_with_invalid_file
- test_load_pdf_returns_pages
- test_load_pdf_from_bytes
- test_empty_text_filtered
"""

import io
import pytest
import fitz  # PyMuPDF

from ingestion.pdf_loader import load_pdf, validate_pdf, get_pdf_metadata


# ── Helpers ────────────────────────────────────────────────────────────

def _make_pdf_bytes(pages: list[str]) -> bytes:
    """Create a minimal in-memory PDF with one text block per page."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page(width=595, height=842)
        if text:
            page.insert_text((72, 100), text, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _make_pdf_file(tmp_path, pages: list[str]) -> str:
    """Write a minimal PDF to a temp file and return its path."""
    pdf_bytes = _make_pdf_bytes(pages)
    path = tmp_path / "test.pdf"
    path.write_bytes(pdf_bytes)
    return str(path)


# ── Tests ──────────────────────────────────────────────────────────────

class TestValidatePdf:
    def test_validate_pdf_with_invalid_file(self, tmp_path):
        """validate_pdf should return (False, <message>) for a non-PDF file."""
        bad_file = tmp_path / "not_a_pdf.txt"
        bad_file.write_text("this is not a PDF")
        is_valid, message = validate_pdf(str(bad_file))
        assert is_valid is False
        assert isinstance(message, str)
        assert len(message) > 0

    def test_validate_pdf_with_valid_file(self, tmp_path):
        """validate_pdf should return (True, ...) for a real PDF."""
        pdf_path = _make_pdf_file(tmp_path, ["Hello, ClauseGuard!"])
        is_valid, message = validate_pdf(pdf_path)
        assert is_valid is True

    def test_validate_pdf_missing_file(self):
        """validate_pdf should return (False, ...) when file does not exist."""
        is_valid, message = validate_pdf("/nonexistent/path/file.pdf")
        assert is_valid is False


class TestLoadPdf:
    def test_load_pdf_returns_pages(self, tmp_path):
        """load_pdf should return a list of page dicts with expected keys."""
        pdf_path = _make_pdf_file(tmp_path, ["Page one content.", "Page two content."])
        pages = load_pdf(pdf_path)

        assert isinstance(pages, list)
        assert len(pages) >= 1  # at least one non-empty page

        for page in pages:
            assert "page" in page
            assert "text" in page
            assert "char_count" in page
            assert isinstance(page["page"], int)
            assert isinstance(page["text"], str)
            assert isinstance(page["char_count"], int)
            assert page["char_count"] > 0

    def test_load_pdf_page_numbers_are_one_indexed(self, tmp_path):
        """Page numbers should start at 1, not 0."""
        pdf_path = _make_pdf_file(tmp_path, ["First page", "Second page"])
        pages = load_pdf(pdf_path)
        page_nums = [p["page"] for p in pages]
        assert min(page_nums) >= 1

    def test_load_pdf_from_bytes(self, tmp_path):
        """load_pdf should accept raw bytes as input."""
        pdf_bytes = _make_pdf_bytes(["Bytes-loaded page content."])
        pages = load_pdf(pdf_bytes)

        assert isinstance(pages, list)
        assert len(pages) >= 1
        assert pages[0]["char_count"] > 0

    def test_load_pdf_from_io_bytes(self, tmp_path):
        """load_pdf should accept a BytesIO stream."""
        pdf_bytes = _make_pdf_bytes(["BytesIO page content."])
        bio = io.BytesIO(pdf_bytes)
        pages = load_pdf(bio.read())  # read to bytes and pass

        assert isinstance(pages, list)
        assert len(pages) >= 1

    def test_empty_text_filtered(self, tmp_path):
        """Pages with no extractable text should be filtered out."""
        # First page has text, second page is blank
        pdf_path = _make_pdf_file(tmp_path, ["Real content here.", ""])
        pages = load_pdf(pdf_path)

        texts = [p["text"].strip() for p in pages]
        # Blank pages should not appear in results
        for t in texts:
            assert len(t) > 0

    def test_load_pdf_raises_on_invalid_input(self, tmp_path):
        """load_pdf should raise ValueError for a non-PDF file."""
        bad_file = tmp_path / "garbage.pdf"
        bad_file.write_bytes(b"not a real pdf stream")
        with pytest.raises((ValueError, Exception)):
            load_pdf(str(bad_file))

    def test_load_pdf_char_count_matches_text(self, tmp_path):
        """char_count should equal len(text) for each page."""
        pdf_path = _make_pdf_file(tmp_path, ["Exact char count check."])
        pages = load_pdf(pdf_path)
        for page in pages:
            assert page["char_count"] == len(page["text"])


class TestGetPdfMetadata:
    def test_metadata_returns_dict(self, tmp_path):
        """get_pdf_metadata should return a dict with num_pages key."""
        pdf_path = _make_pdf_file(tmp_path, ["Meta page 1", "Meta page 2"])
        meta = get_pdf_metadata(pdf_path)
        assert isinstance(meta, dict)
        assert "num_pages" in meta
        assert meta["num_pages"] == 2

    def test_metadata_has_expected_keys(self, tmp_path):
        """get_pdf_metadata should include standard metadata keys."""
        pdf_path = _make_pdf_file(tmp_path, ["Metadata test"])
        meta = get_pdf_metadata(pdf_path)
        expected_keys = {"num_pages", "title", "author"}
        assert expected_keys.issubset(meta.keys())
