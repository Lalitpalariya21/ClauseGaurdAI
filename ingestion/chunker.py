"""
ingestion/chunker.py
====================
Sliding-window text chunking for ClauseGuard AI.
Preserves page metadata and handles both per-page and raw text chunking.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

try:
    from config.settings import CHUNK_OVERLAP, CHUNK_SIZE
except ImportError:
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150

logger = logging.getLogger(__name__)


def _split_text(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[tuple[int, int]]:
    """Return (start, end) character-offset pairs for sliding-window chunks."""
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be > 0, got {chunk_size}")
    if overlap < 0:
        raise ValueError(f"overlap must be >= 0, got {overlap}")
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size}).")

    n = len(text)
    if n == 0:
        return []

    step = chunk_size - overlap
    spans: list[tuple[int, int]] = []
    start = 0

    while start < n:
        end = min(start + chunk_size, n)
        spans.append((start, end))
        if end == n:
            break
        start += step

    return spans


def chunk_pages(
    pages: list[dict],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    chunk_overlap: Optional[int] = None,
) -> list[dict]:
    """Split a list of page dicts into overlapping text chunks with page tracking."""
    actual_overlap = chunk_overlap if chunk_overlap is not None else overlap

    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be > 0, got {chunk_size}")
    if actual_overlap < 0:
        raise ValueError(f"overlap must be >= 0, got {actual_overlap}")
    if actual_overlap >= chunk_size:
        raise ValueError(f"overlap ({actual_overlap}) must be less than chunk_size ({chunk_size}).")

    chunks: list[dict] = []
    chunk_id = 0

    for page_dict in pages:
        page_num: int = page_dict.get("page", 1)
        text: str = page_dict.get("text", "")

        if not text or not text.strip():
            continue

        spans = _split_text(text, chunk_size, actual_overlap)

        for start, end in spans:
            c_text = text[start:end]
            chunk: dict[str, Any] = {
                "chunk_id": chunk_id,
                "text": c_text,
                "page": page_num,
                "start_char": start,
                "end_char": end,
            }
            chunks.append(chunk)
            chunk_id += 1

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    chunk_overlap: Optional[int] = None,
) -> list[dict]:
    """Split a raw text string into chunks."""
    actual_overlap = chunk_overlap if chunk_overlap is not None else overlap
    pages = [{"page": 1, "text": text, "char_count": len(text)}]
    return chunk_pages(pages, chunk_size=chunk_size, overlap=actual_overlap)


def get_full_text(pages: list[dict]) -> str:
    """Concatenate all page texts into a single string."""
    return "\n\n".join(p.get("text", "") for p in pages if p.get("text", "").strip())
