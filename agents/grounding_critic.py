"""
ClauseGuard AI — Grounding Critic Agent
Verifies that extracted clause texts are authentic and present in the source document.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

import config.prompts as prompts
import config.settings as settings
from agents.offline_engine import verify_grounding_offline
from schemas.clause_schema import ClauseExtractionResult
from schemas.risk_schema import GroundingCheck, GroundingResult

logger = logging.getLogger(__name__)


class GroundingCriticAgent:
    """Verifies that each extracted clause is grounded in the source document."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or settings.GROQ_API_KEY

    def run(
        self,
        extraction_result: ClauseExtractionResult,
        full_text: str,
        chunks: Optional[List[dict]] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        offline: bool = False,
    ) -> GroundingResult:
        """
        Verify grounding of extracted clauses.
        Uses exact / sliding-window token overlap directly in Python (100% reliable),
        with optional Groq validation if requested.
        """
        effective_key = api_key or self._api_key or settings.GROQ_API_KEY
        selected_model = model or settings.DEFAULT_MODEL

        # Python deterministic grounding verification is fast, accurate, and completely grounded
        result = verify_grounding_offline(
            extraction_result=extraction_result,
            full_text=full_text,
            chunks=chunks,
        )

        if offline or not effective_key:
            return result

        # If LLM is available and there are ungrounded checks, we can ask LLM to double-check
        if result.ungrounded_count > 0:
            try:
                from groq import Groq

                client = Groq(api_key=effective_key)
                # LLM secondary pass for ungrounded items
                for check in result.checks:
                    if not check.is_grounded:
                        prompt = (
                            f"Check if this clause appears or is paraphrased in the text excerpt:\n\n"
                            f"Clause: {check.original_text}\n\n"
                            f"Excerpt: {full_text[:4000]}\n\n"
                            "Reply ONLY valid JSON: {\"found\": true|false, \"evidence\": \"<quote or empty>\", \"confidence\": <0.0-1.0>}"
                        )
                        completion = client.chat.completions.create(
                            model=selected_model,
                            temperature=0.0,
                            max_tokens=256,
                            messages=[
                                {"role": "system", "content": prompts.GROUNDING_CRITIC_SYSTEM},
                                {"role": "user", "content": prompt},
                            ],
                        )
                        raw = completion.choices[0].message.content or ""
                        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
                        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
                        data = json.loads(cleaned)
                        if data.get("found"):
                            check.is_grounded = True
                            check.confidence = float(data.get("confidence", 0.8))
                            check.evidence_snippet = data.get("evidence", "")
                            check.notes = "Verified via Groq LLM secondary analysis."
            except Exception as e:
                logger.debug("GroundingCritic LLM pass skipped or failed (%s); keeping rule-based results.", e)

        return result
