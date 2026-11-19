"""
services/qa_service.py
======================
RAG-powered Q&A service that answers user queries based on the loaded contract.
Supports both Groq LLM API and the zero-dependency Offline RAG Engine.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import config.settings as settings
from agents.offline_engine import answer_rag_offline
from config.prompts import RAG_QA_SYSTEM
from rag.retriever import Retriever

logger = logging.getLogger(__name__)

_HISTORY_TURNS = 4


class QAService:
    """Answers natural-language questions about a contract using RAG."""

    def __init__(
        self,
        retriever: Retriever,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._retriever = retriever
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model = model or settings.DEFAULT_MODEL

    def answer(
        self,
        question: str,
        chat_history: Optional[List[dict]] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        offline: bool = False,
    ) -> dict:
        """Answer a question about the loaded contract."""
        q = (question or "").strip()
        if not q:
            return {
                "answer": "Please ask a question about the contract.",
                "sources": [],
                "confidence": "Low",
            }

        effective_key = api_key or self._api_key or settings.GROQ_API_KEY
        selected_model = model or self._model or settings.DEFAULT_MODEL

        # Retrieve relevant chunks from vector index
        retrieved = self._retriever.retrieve(q, top_k=settings.FAISS_TOP_K)
        relevant = [c for c in retrieved if (c.get("text") or "").strip()]

        if not relevant:
            return {
                "answer": "This information was not found in the document.",
                "sources": [],
                "confidence": "Low",
            }

        # Offline mode or no API key available
        if offline or not effective_key:
            return answer_rag_offline(q, relevant)

        # Groq API mode
        try:
            from groq import Groq

            client = Groq(api_key=effective_key)

            context_snippets = []
            sources = []
            for c in relevant[:3]:
                page = c.get("page", 1)
                txt = c.get("text", "").strip()
                score = c.get("score", 0.0)
                context_snippets.append(f"[Page {page}] {txt}")
                sources.append(
                    {
                        "page": page,
                        "text": txt[:300] + ("..." if len(txt) > 300 else ""),
                        "score": score,
                    }
                )

            context_str = "\n\n".join(context_snippets)

            # Build messages with history
            messages = [{"role": "system", "content": RAG_QA_SYSTEM}]

            if chat_history:
                recent = chat_history[-_HISTORY_TURNS:]
                for turn in recent:
                    role = turn.get("role", "user")
                    content = turn.get("content", "")
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": content})

            user_msg = (
                f"Retrieved contract passages:\n\n{context_str}\n\n"
                f"Question: {q}\n\n"
                "Answer the question concisely using ONLY the retrieved context. "
                "Always cite the source page number(s)."
            )
            messages.append({"role": "user", "content": user_msg})

            completion = client.chat.completions.create(
                model=selected_model,
                temperature=0.1,
                max_tokens=512,
                messages=messages,
            )
            answer_text = completion.choices[0].message.content or ""

            return {
                "answer": answer_text,
                "sources": sources,
                "confidence": "High",
            }
        except Exception as exc:
            logger.warning("Groq QA failed (%s); falling back to offline answer engine.", exc)
            return answer_rag_offline(q, relevant)
