"""
rag/vector_store.py
===================
Vector store for ClauseGuard AI.
Uses FAISS IndexFlatIP if available, or high-performance NumPy cosine similarity
as an automatic fallback.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """Return L2-normalised copy of vectors (float32, shape N×D)."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return (vectors / norms).astype(np.float32)


class VectorStore:
    """Vector store for chunk retrieval supporting FAISS and NumPy."""

    def __init__(self) -> None:
        self._index: Optional[Any] = None
        self._vectors: Optional[np.ndarray] = None
        self._metadata: List[dict] = []
        self._embedding_dim: Optional[int] = None
        self._use_faiss: bool = False

        try:
            import faiss
            self._faiss = faiss
            self._use_faiss = True
        except ImportError:
            self._faiss = None
            self._use_faiss = False
            logger.info("FAISS not found; using NumPy cosine similarity engine.")

    @property
    def total_vectors(self) -> int:
        return len(self._metadata)

    def build(self, chunks: List[dict], embeddings: np.ndarray) -> None:
        """Build vector index from precomputed embeddings."""
        if len(chunks) == 0:
            raise ValueError("chunks must be non-empty.")
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be a 2-D array of shape (N, D).")
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"Length mismatch: {len(chunks)} chunks vs {embeddings.shape[0]} embeddings."
            )

        dim = embeddings.shape[1]
        normalised = _l2_normalize(embeddings)

        self._embedding_dim = dim
        self._metadata = [dict(chunk) for chunk in chunks]
        self._vectors = normalised

        if self._use_faiss and self._faiss is not None:
            try:
                index = self._faiss.IndexFlatIP(dim)
                index.add(normalised)
                self._index = index
                logger.info("FAISS IndexFlatIP built with %d vectors (dim=%d).", index.ntotal, dim)
                return
            except Exception as e:
                logger.warning("FAISS index creation failed (%s); using NumPy fallback.", e)
                self._use_faiss = False

        logger.info("NumPy vector index built with %d vectors (dim=%d).", len(chunks), dim)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[dict]:
        """Return top_k most similar chunks for query vector."""
        if self._vectors is None or len(self._metadata) == 0:
            return []

        # Prepare 1-D query vector
        q = query_embedding.astype(np.float32).flatten()
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm
        else:
            q = np.zeros_like(q)
            q[0] = 1.0

        k = min(top_k, len(self._metadata))

        if self._use_faiss and self._index is not None:
            try:
                q_2d = q.reshape(1, -1)
                scores, indices = self._index.search(q_2d, k)
                results: List[dict] = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx >= 0 and idx < len(self._metadata):
                        hit = dict(self._metadata[idx])
                        hit["score"] = float(score)
                        results.append(hit)
                return results
            except Exception as e:
                logger.warning("FAISS search failed (%s); falling back to NumPy dot.", e)

        # NumPy cosine similarity
        scores = np.dot(self._vectors, q)
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_indices:
            hit = dict(self._metadata[idx])
            hit["score"] = float(scores[idx])
            results.append(hit)

        return results

    def save(self, path: str) -> None:
        """Persist vector store metadata and vectors."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            pickle.dump(
                {
                    "vectors": self._vectors,
                    "metadata": self._metadata,
                    "dim": self._embedding_dim,
                },
                f,
            )

    def load(self, path: str) -> None:
        """Load vector store metadata and vectors."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._vectors = data.get("vectors")
        self._metadata = data.get("metadata", [])
        self._embedding_dim = data.get("dim")
        if self._vectors is not None and len(self._metadata) > 0:
            self.build(self._metadata, self._vectors)
