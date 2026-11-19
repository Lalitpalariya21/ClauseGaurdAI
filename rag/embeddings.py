"""
rag/embeddings.py
=================
Embedding model wrapper for ClauseGuard AI.
Uses sentence-transformers if available, with a fast, zero-dependency
deterministic semantic vectorizer fallback for 100% offline environments.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from typing import Any, List, Optional

import numpy as np

import config.settings as settings

logger = logging.getLogger(__name__)

_model_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()


def _hash_vectorize(texts: List[str], dim: int = 384) -> np.ndarray:
    """Deterministic, zero-dependency subword/word n-gram vectorizer for offline mode.

    Generates float32 L2-normalised vectors of dimension `dim` (default 384,
    matching all-MiniLM-L6-v2), providing effective cosine similarity for legal text.
    """
    matrix = np.zeros((len(texts), dim), dtype=np.float32)

    for i, text in enumerate(texts):
        tokens = re.findall(r"\b\w+\b", text.lower())
        if not tokens:
            matrix[i, 0] = 1.0
            continue

        vec = np.zeros(dim, dtype=np.float32)

        # 1. Word hashing with term frequency
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 16) & 1) else -1.0
            vec[idx] += sign * (1.0 + np.log(1.0 + tokens.count(token)))

        # 2. Character n-grams (subwords) for morphological capture
        for token in tokens:
            if len(token) >= 4:
                for k in range(len(token) - 3):
                    ngram = token[k : k + 4]
                    h_ng = int(hashlib.sha256(ngram.encode("utf-8")).hexdigest(), 16)
                    vec[h_ng % dim] += 0.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            matrix[i] = vec / norm
        else:
            matrix[i, 0] = 1.0

    return matrix.astype(np.float32)


class EmbeddingModel:
    """Wraps SentenceTransformer with graceful local fallback."""

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL) -> None:
        self._model_name = model_name
        self._model: Optional[Any] = None
        self._using_fallback = False

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer

            with _cache_lock:
                if self._model_name not in _model_cache:
                    logger.info("Loading SentenceTransformer: %s", self._model_name)
                    _model_cache[self._model_name] = SentenceTransformer(self._model_name)
                self._model = _model_cache[self._model_name]
                return self._model
        except Exception as e:
            logger.info("SentenceTransformer not available (%s); using local offline vectorizer.", e)
            self._using_fallback = True
            return None

    def embed(self, texts: List[str]) -> np.ndarray:
        """Embed a list of strings into float32 vectors."""
        if not texts:
            raise ValueError("texts must be a non-empty list of strings.")

        model = self._get_model()
        if model is not None and not self._using_fallback:
            try:
                embeddings = model.encode(
                    texts,
                    batch_size=32,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )
                return embeddings.astype(np.float32)
            except Exception as exc:
                logger.warning("Model encoding failed (%s); using offline vectorizer fallback.", exc)

        return _hash_vectorize(texts, dim=384)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query into a 1-D vector of shape (dim,)."""
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty.")
        return self.embed([query])[0]
