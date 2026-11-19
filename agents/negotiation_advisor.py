"""
ClauseGuard AI — Negotiation Advisor Agent
Generates actionable negotiation advice and contract rewrites using Groq LLM or Offline Rules.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

import config.prompts as prompts
import config.settings as settings
from agents.offline_engine import advise_negotiation_offline
from schemas.clause_schema import ClauseExtractionResult
from schemas.risk_schema import NegotiationPoint, NegotiationResult, RiskAuditResult

logger = logging.getLogger(__name__)


class NegotiationAdvisorAgent:
    """Produces actionable negotiation advice for concerning contract clauses."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or settings.GROQ_API_KEY

    def _build_user_prompt(self, concerning: list[dict], doc_type: str) -> str:
        clauses_json = json.dumps(concerning, indent=2)
        return (
            f"Document type: {doc_type}\n\n"
            "## Concerning Clauses (Medium or High Risk)\n\n"
            f"```json\n{clauses_json}\n```\n\n"
            "For each clause, provide a plain-English explanation, suggested alternative wording, "
            "and negotiation tips as defined in the schema. Output ONLY valid JSON."
        )

    def _parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        return json.loads(cleaned)

    def run(
        self,
        extraction_result: ClauseExtractionResult,
        risk_result: RiskAuditResult,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        offline: bool = False,
    ) -> NegotiationResult:
        """
        Produce negotiation recommendations for High & Medium risk clauses.
        """
        concerning = [
            item.model_dump()
            for item in risk_result.risk_items
            if item.risk_level in ("High", "Medium")
        ]

        if not concerning:
            return NegotiationResult(
                points=[],
                executive_summary=(
                    "No high or medium risk clauses were identified. The contract terms appear standard "
                    "and balanced, though consulting qualified legal counsel is always recommended."
                ),
            )

        effective_key = api_key or self._api_key or settings.GROQ_API_KEY
        selected_model = model or settings.DEFAULT_MODEL

        if offline or not effective_key:
            logger.info("Running NegotiationAdvisorAgent in Offline Mode (no API call).")
            return advise_negotiation_offline(risk_result)

        try:
            from groq import Groq

            client = Groq(api_key=effective_key)
            user_prompt = self._build_user_prompt(concerning, extraction_result.document_type)

            completion = client.chat.completions.create(
                model=selected_model,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": prompts.NEGOTIATION_ADVISOR_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw_response = completion.choices[0].message.content or ""
            data = self._parse_response(raw_response)

            points: List[NegotiationPoint] = []
            for p in data.get("points", []):
                try:
                    points.append(NegotiationPoint(**p))
                except Exception as e:
                    logger.warning("Skipping malformed negotiation point: %s (%s)", p, e)

            exec_summary = data.get("executive_summary", "Review the suggested alternative wording above.")
            return NegotiationResult(
                points=points,
                executive_summary=exec_summary,
            )
        except Exception as exc:
            logger.warning("Groq API failed in NegotiationAdvisorAgent (%s); using offline recommendations.", exc)
            return advise_negotiation_offline(risk_result)
