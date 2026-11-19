"""
rag/retriever.py
================
High-level retriever that combines EmbeddingModel and VectorStore.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Union

import config.settings as settings
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Orchestrates embedding and retrieval for ClauseGuard AI."""

    def __init__(
        self,
        chunks_or_model: Optional[Union[List[dict], str]] = None,
        chunks: Optional[List[dict]] = None,
        model_name: str = settings.EMBEDDING_MODEL,
        store: Optional[VectorStore] = None,
    ) -> None:
        actual_chunks: Optional[List[dict]] = chunks
        actual_model: str = model_name

        if isinstance(chunks_or_model, list):
            actual_chunks = chunks_or_model
        elif isinstance(chunks_or_model, str):
            actual_model = chunks_or_model

        self._embedding_model = EmbeddingModel(model_name=actual_model)
        self._store = store if store is not None else VectorStore()
        self._chunks: List[dict] = []

        if actual_chunks:
            self.build_index(actual_chunks)

    @property
    def chunks(self) -> List[dict]:
        return self._chunks

    def build_index(self, chunks: List[dict]) -> None:
        """Embed chunks and build the vector index."""
        if not chunks:
            raise ValueError("chunks must be a non-empty list.")

        self._chunks = list(chunks)
        texts = [c.get("text", "") for c in chunks]
        logger.info("Building vector index for %d chunks...", len(texts))

        embeddings = self._embedding_model.embed(texts)
        self._store.build(chunks, embeddings)

    def retrieve(
        self,
        query: str,
        top_k: int = settings.FAISS_TOP_K,
    ) -> List[dict]:
        """Retrieve most relevant chunks for a natural-language query."""
        if not query or not query.strip():
            return []

        query_vec = self._embedding_model.embed_query(query)
        return self._store.search(query_vec, top_k=top_k)

    def format_context(self, hits: List[dict]) -> str:
        """Format retrieved chunks as readable context text."""
        sections = []
        for i, h in enumerate(hits, 1):
            page = h.get("page", "?")
            text = h.get("text", "")
            score = h.get("score")
            score_str = f" (score: {score:.3f})" if score is not None else ""
            sections.append(f"[Excerpt {i} | Page {page}{score_str}]\n{text}")
        return "\n\n---\n\n".join(sections)
