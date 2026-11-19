"""
ingestion/pdf_loader.py
=======================
PDF loading utilities for ClauseGuard AI.

Responsibilities
----------------
- Load a PDF from a file path or raw bytes using PyMuPDF (fitz).
- Return per-page text with metadata.
- Validate PDF integrity.
- Extract document-level metadata.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Union

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
_Source = Union[str, Path, bytes]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _open_document(source: _Source) -> fitz.Document:
    """Open a fitz.Document from a file path or raw bytes.

    Parameters
    ----------
    source:
        A file-system path (str or Path) **or** the raw PDF bytes.

    Returns
    -------
    fitz.Document
        An open (but not yet read) document handle.

    Raises
    ------
    FileNotFoundError
        If *source* is a path and the file does not exist.
    ValueError
        If *source* has an unexpected type.
    fitz.FileDataError
        Propagated from PyMuPDF when the bytes are not a valid PDF.
    """
    if isinstance(source, bytes):
        return fitz.open(stream=source, filetype="pdf")
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    return fitz.open(str(path))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_pdf(source: _Source) -> list[dict]:
    """Load a PDF and return per-page text as a list of dicts.

    Each dict has the shape::

        {
            "page": int,        # 1-based page number
            "text": str,        # extracted text (may be empty for image pages)
            "char_count": int,  # len(text)
        }

    Parameters
    ----------
    source:
        File path (str / Path) or raw PDF bytes.

    Returns
    -------
    list[dict]
        One entry per page.

    Raises
    ------
    FileNotFoundError
        When *source* is a path that does not exist.
    ValueError
        When the PDF is empty, unreadable, or yields no pages.
    RuntimeError
        When the PDF is encrypted and cannot be decrypted.
    """
    doc: fitz.Document | None = None
    try:
        doc = _open_document(source)

        # --- Handle encryption -------------------------------------------------
        if doc.is_encrypted:
            # Attempt decryption with an empty password (many "protected" PDFs
            # are only owner-locked, so an empty user password works).
            auth_result = doc.authenticate("")
            if auth_result == 0:
                logger.warning(
                    "PDF is encrypted and could not be decrypted with an empty "
                    "password.  Returning empty page list."
                )
                raise RuntimeError(
                    "PDF is password-protected. Please provide the decryption "
                    "password before loading."
                )

        if doc.page_count == 0:
            raise ValueError("PDF contains no pages.")

        pages: list[dict] = []
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page.get_text("text")  # plain-text extraction
            if text and text.strip():
                pages.append(
                    {
                        "page": page_index + 1,  # 1-based
                        "text": text,
                        "char_count": len(text),
                    }
                )

        if not pages:
            raise ValueError("PDF loaded but yielded no page data.")

        total_chars = sum(p["char_count"] for p in pages)
        if total_chars == 0:
            raise ValueError(
                "PDF appears to be a scanned image-only document with no "
                "extractable text.  Consider running OCR first."
            )

        logger.info(
            "Loaded PDF: %d pages, %d total chars.",
            len(pages),
            total_chars,
        )
        return pages

    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc
    finally:
        if doc is not None:
            doc.close()


def validate_pdf(source: _Source) -> tuple[bool, str]:
    """Validate that *source* is a readable, non-empty PDF.

    Parameters
    ----------
    source:
        File path or raw bytes.

    Returns
    -------
    tuple[bool, str]
        ``(True, "Valid PDF")`` on success, or
        ``(False, "<reason>")`` on any problem.
    """
    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            return False, f"File does not exist: {p}"
        if p.suffix.lower() != ".pdf":
            return False, "File does not have a .pdf extension."
    elif isinstance(source, bytes):
        if not source.startswith(b"%PDF"):
            return False, "Bytes do not contain valid PDF header (%PDF)."

    doc: fitz.Document | None = None
    try:
        doc = _open_document(source)

        if doc.is_encrypted:
            auth = doc.authenticate("")
            if auth == 0:
                return False, "PDF is password-protected and could not be decrypted."

        if doc.page_count == 0:
            return False, "PDF contains no pages."

        # Quick text check on first page
        first_page = doc.load_page(0)
        sample_text = first_page.get_text("text").strip()

        if not sample_text and doc.page_count == 1:
            return (
                False,
                "PDF appears to be an image-only scan with no extractable text.",
            )

        return True, f"Valid PDF with {doc.page_count} page(s)."

    except FileNotFoundError as exc:
        return False, str(exc)
    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        return False, f"Corrupt or unreadable PDF: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error during validation: {exc}"
    finally:
        if doc is not None:
            doc.close()


def get_pdf_metadata(source: _Source) -> dict:
    """Extract document-level metadata from a PDF.

    Returns a dict with at least the following keys (values may be empty
    strings or ``None`` if the PDF does not expose the field):

    .. code-block:: python

        {
            "title":        str,
            "author":       str,
            "subject":      str,
            "keywords":     str,
            "creator":      str,       # producing application
            "producer":     str,       # PDF library used to write the file
            "creation_date": str,
            "mod_date":     str,
            "num_pages":    int,
            "file_size_bytes": int,    # only when source is a path
            "is_encrypted": bool,
            "pdf_version":  str,
        }

    Parameters
    ----------
    source:
        File path or raw bytes.

    Returns
    -------
    dict
        Metadata mapping.

    Raises
    ------
    FileNotFoundError
        When *source* is a path that does not exist.
    ValueError
        When the file is not a valid PDF.
    """
    doc: fitz.Document | None = None
    try:
        doc = _open_document(source)
        raw_meta: dict = doc.metadata or {}

        metadata: dict = {
            "title": raw_meta.get("title", ""),
            "author": raw_meta.get("author", ""),
            "subject": raw_meta.get("subject", ""),
            "keywords": raw_meta.get("keywords", ""),
            "creator": raw_meta.get("creator", ""),
            "producer": raw_meta.get("producer", ""),
            "creation_date": raw_meta.get("creationDate", ""),
            "mod_date": raw_meta.get("modDate", ""),
            "num_pages": doc.page_count,
            "is_encrypted": doc.is_encrypted,
            "pdf_version": doc.pdf_version() if hasattr(doc, "pdf_version") else "",
        }

        # File size is only available when source is a path
        if not isinstance(source, bytes):
            path = Path(source)
            metadata["file_size_bytes"] = path.stat().st_size if path.exists() else None
        else:
            metadata["file_size_bytes"] = len(source)

        return metadata

    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise ValueError(f"Could not read PDF metadata: {exc}") from exc
    finally:
        if doc is not None:
            doc.close()
