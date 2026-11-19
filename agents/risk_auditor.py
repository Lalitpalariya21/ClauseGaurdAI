"""
ClauseGuard AI — Risk Auditor Agent
Evaluates extracted clauses for legal / contractual risk using Groq LLM or Offline Rules.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

import config.prompts as prompts
import config.settings as settings
from agents.offline_engine import audit_risks_offline
from schemas.clause_schema import ClauseExtractionResult
from schemas.risk_schema import RiskAuditResult, RiskItem, RiskLevel

logger = logging.getLogger(__name__)


class RiskAuditorAgent:
    """Audits extracted clauses and assigns risk levels via Groq or Offline Engine."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or settings.GROQ_API_KEY

    def _build_user_prompt(self, extraction_result: ClauseExtractionResult) -> str:
        clauses_json = json.dumps(
            [c.model_dump() for c in extraction_result.clauses], indent=2
        )
        return (
            f"Document type: {extraction_result.document_type}\n\n"
            "## Extracted Clauses\n\n"
            f"```json\n{clauses_json}\n```\n\n"
            "Audit each clause for risk according to the specified schema. Output ONLY valid JSON."
        )

    def _parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        return json.loads(cleaned)

    def run(
        self,
        extraction_result: ClauseExtractionResult,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        offline: bool = False,
    ) -> RiskAuditResult:
        """
        Audit extracted clauses. If offline=True or no API key, runs offline engine.
        """
        if not extraction_result.clauses:
            return RiskAuditResult(
                risk_items=[],
                overall_risk_level="Low",
                high_count=0,
                medium_count=0,
                low_count=0,
                audit_summary="No clauses identified to audit.",
            )

        effective_key = api_key or self._api_key or settings.GROQ_API_KEY
        selected_model = model or settings.DEFAULT_MODEL

        if offline or not effective_key:
            logger.info("Running RiskAuditorAgent in Offline Mode (no API call).")
            return audit_risks_offline(extraction_result)

        try:
            from groq import Groq

            client = Groq(api_key=effective_key)
            user_prompt = self._build_user_prompt(extraction_result)

            completion = client.chat.completions.create(
                model=selected_model,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": prompts.RISK_AUDITOR_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw_response = completion.choices[0].message.content or ""
            data = self._parse_response(raw_response)

            items: List[RiskItem] = []
            for r in data.get("risk_items", []):
                try:
                    items.append(RiskItem(**r))
                except Exception as e:
                    logger.warning("Skipping malformed risk item: %s (%s)", r, e)

            high = sum(1 for i in items if i.risk_level == "High")
            medium = sum(1 for i in items if i.risk_level == "Medium")
            low = sum(1 for i in items if i.risk_level == "Low")
            overall = data.get("overall_risk_level", "High" if high > 0 else ("Medium" if medium > 0 else "Low"))
            summary = data.get("audit_summary", "Audit completed via Groq LLM.")

            return RiskAuditResult(
                risk_items=items,
                overall_risk_level=overall,
                high_count=high,
                medium_count=medium,
                low_count=low,
                audit_summary=summary,
            )
        except Exception as exc:
            logger.warning("Groq API failed in RiskAuditorAgent (%s); falling back to offline audit.", exc)
            return audit_risks_offline(extraction_result)
