"""
ClauseGuard AI — Clause Extractor Agent
Extracts contract clauses using either Groq LLM or the Offline Legal Intelligence Engine.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

import config.prompts as prompts
import config.settings as settings
from agents.offline_engine import extract_clauses_offline
from schemas.clause_schema import ClauseExtractionResult, ExtractedClause

logger = logging.getLogger(__name__)


class ClauseExtractorAgent:
    """Extracts key clauses from a contract using Groq or the local heuristic engine."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or settings.GROQ_API_KEY

    def _build_user_prompt(self, full_text: str, retrieved_chunks: List[dict]) -> str:
        chunks_text = "\n\n---\n\n".join(
            f"[Chunk {i+1} | Page {c.get('page', '?')}]\n{c.get('text', '')}"
            for i, c in enumerate(retrieved_chunks)
        )
        return (
            "You are analysing the following contract document.\n\n"
            "## Retrieved Context Chunks (from RAG)\n\n"
            f"{chunks_text}\n\n"
            "## Full Document Text (first 6000 chars)\n\n"
            f"{full_text[:6000]}\n\n"
            "Extract all relevant clauses as instructed. Output ONLY valid JSON."
        )

    def _parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        return json.loads(cleaned)

    def run(
        self,
        full_text: str,
        retrieved_chunks: List[dict],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        offline: bool = False,
    ) -> ClauseExtractionResult:
        """
        Execute clause extraction. Uses local engine if offline is True or
        no valid API key is present. Otherwise calls Groq LLM.
        """
        effective_key = api_key or self._api_key or settings.GROQ_API_KEY
        selected_model = model or settings.DEFAULT_MODEL

        # If offline requested or no key provided, run offline legal engine
        if offline or not effective_key:
            logger.info("Running ClauseExtractorAgent in Offline Mode (no API call).")
            return extract_clauses_offline(full_text=full_text, chunks=retrieved_chunks)

        # Groq API path
        try:
            from groq import Groq

            client = Groq(api_key=effective_key)
            user_prompt = self._build_user_prompt(full_text, retrieved_chunks)

            completion = client.chat.completions.create(
                model=selected_model,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": prompts.CLAUSE_EXTRACTOR_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw_response = completion.choices[0].message.content or ""
            data = self._parse_response(raw_response)

            clauses: List[ExtractedClause] = []
            for c in data.get("clauses", []):
                try:
                    clauses.append(ExtractedClause(**c))
                except Exception as e:
                    logger.warning("Skipping malformed clause: %s (%s)", c, e)

            doc_type = data.get("document_type", "Commercial Agreement")
            missing = data.get("missing_clause_types", [])

            return ClauseExtractionResult(
                document_type=doc_type,
                clauses=clauses,
                missing_clause_types=missing,
                raw_llm_response=raw_response,
            )
        except Exception as exc:
            logger.warning("Groq API failed in ClauseExtractorAgent (%s); falling back to offline engine.", exc)
            res = extract_clauses_offline(full_text=full_text, chunks=retrieved_chunks)
            res.raw_llm_response = f"Fallback after API error: {exc}"
            return res
