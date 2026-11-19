"""
ingestion/text_cleaner.py
=========================
Text normalisation utilities for ClauseGuard AI.

Responsibilities
----------------
- Strip control characters and exotic Unicode noise.
- Fix broken hyphenation that PDF extractors produce at line ends.
- Normalise typographic quotes and dashes to their ASCII equivalents.
- Collapse redundant whitespace and blank lines.
- Filter out near-empty pages that would pollute embeddings.
"""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Minimum number of meaningful (non-whitespace) characters a page must have
#: to be retained after cleaning.
_MIN_MEANINGFUL_CHARS: int = 20

# Typographic → ASCII quote / dash maps
_QUOTE_MAP: dict[str, str] = {
    "\u2018": "'",   # LEFT SINGLE QUOTATION MARK
    "\u2019": "'",   # RIGHT SINGLE QUOTATION MARK
    "\u201a": "'",   # SINGLE LOW-9 QUOTATION MARK
    "\u201b": "'",   # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    "\u201c": '"',   # LEFT DOUBLE QUOTATION MARK
    "\u201d": '"',   # RIGHT DOUBLE QUOTATION MARK
    "\u201e": '"',   # DOUBLE LOW-9 QUOTATION MARK
    "\u201f": '"',   # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
    "\u2032": "'",   # PRIME
    "\u2033": '"',   # DOUBLE PRIME
    "\u2014": "--",  # EM DASH
    "\u2013": "-",   # EN DASH
    "\u2012": "-",   # FIGURE DASH
    "\u2010": "-",   # HYPHEN
    "\u00ab": '"',   # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    "\u00bb": '"',   # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
}

# Pre-compiled regex patterns
_RE_BROKEN_HYPHEN = re.compile(r"(\w)-\n(\w)")          # word-\nword → wordword
_RE_NEWLINE_SPACE  = re.compile(r"\n[ \t]+")             # trailing whitespace after newline
_RE_MULTI_SPACE    = re.compile(r"[ \t]{2,}")            # 2+ spaces/tabs → single space
_RE_MULTI_NEWLINE  = re.compile(r"\n{3,}")               # 3+ blank lines → 2
_RE_CONTROL_CHARS  = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")  # keep \t \n
_RE_UNICODE_NOISE  = re.compile(r"[\ufffd\ufffe\uffff]") # Unicode replacement / BOM


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalise raw PDF-extracted text into clean prose.

    Processing steps (in order):

    1. Strip Unicode noise and control characters.
    2. Normalise typographic quotes and dashes to ASCII equivalents.
    3. Fix broken hyphenation (``word-\\nword`` → ``wordword``).
    4. Collapse multiple spaces / tabs to a single space.
    5. Remove trailing whitespace on each line.
    6. Collapse 3+ consecutive blank lines to 2.
    7. Strip leading/trailing whitespace from the whole string.

    Parameters
    ----------
    text:
        Raw text as returned by PyMuPDF's ``page.get_text("text")``.

    Returns
    -------
    str
        Cleaned text.
    """
    if not text:
        return ""

    # 1. Strip control characters (keep tab + newline)
    text = _RE_CONTROL_CHARS.sub("", text)
    text = _RE_UNICODE_NOISE.sub("", text)

    # Normalise Unicode to NFC (compose combining characters)
    text = unicodedata.normalize("NFC", text)

    # 2. Normalise typographic quotes / dashes
    for fancy, plain in _QUOTE_MAP.items():
        text = text.replace(fancy, plain)

    # 3. Fix broken hyphenation at line boundaries
    text = _RE_BROKEN_HYPHEN.sub(r"\1\2", text)

    # 4. Collapse multiple spaces / tabs
    text = _RE_MULTI_SPACE.sub(" ", text)

    # 5. Remove trailing whitespace after newlines
    text = _RE_NEWLINE_SPACE.sub("\n", text)

    # 6. Collapse excess blank lines
    text = _RE_MULTI_NEWLINE.sub("\n\n", text)

    # 7. Strip global leading/trailing whitespace
    return text.strip()


def clean_pages(pages: list[dict]) -> list[dict]:
    """Clean text on every page and filter out near-empty pages.

    Applies :func:`clean_text` to the ``"text"`` field of each page dict
    (which must at minimum contain ``"page"`` and ``"text"`` keys).  Pages
    whose cleaned text has fewer than :data:`_MIN_MEANINGFUL_CHARS`
    non-whitespace characters are dropped.

    Parameters
    ----------
    pages:
        List of page dicts as returned by :func:`ingestion.pdf_loader.load_pdf`.
        Each dict must have at least the keys ``"page"`` and ``"text"``.

    Returns
    -------
    list[dict]
        Cleaned and filtered list of page dicts.  Each dict gains an updated
        ``"char_count"`` field reflecting the cleaned text length.

    Examples
    --------
    >>> raw_pages = [{"page": 1, "text": "Hello  World\\n\\n\\n", "char_count": 18}]
    >>> clean_pages(raw_pages)
    [{'page': 1, 'text': 'Hello World', 'char_count': 11}]
    """
    cleaned: list[dict] = []
    dropped = 0

    for page_dict in pages:
        raw_text: str = page_dict.get("text", "")
        cleaned_text = clean_text(raw_text)

        # Count non-whitespace characters for the threshold check
        meaningful_chars = len(cleaned_text.replace(" ", "").replace("\n", "").replace("\t", ""))

        if meaningful_chars < _MIN_MEANINGFUL_CHARS:
            logger.debug(
                "Dropping page %d — only %d meaningful chars after cleaning.",
                page_dict.get("page", "?"),
                meaningful_chars,
            )
            dropped += 1
            continue

        updated = dict(page_dict)   # shallow copy to avoid mutating caller's data
        updated["text"] = cleaned_text
        updated["char_count"] = len(cleaned_text)
        cleaned.append(updated)

    if dropped:
        logger.info(
            "clean_pages: retained %d pages, dropped %d near-empty pages.",
            len(cleaned),
            dropped,
        )

    return cleaned
