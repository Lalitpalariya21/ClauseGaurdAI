"""
ClauseGuard AI — Comprehensive contract report schema (Pydantic v2).

ContractReport ties together clause extraction, risk audit, negotiation advice,
and grounding verification into a single exportable document.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .clause_schema import ClauseExtractionResult
from .risk_schema import GroundingResult, NegotiationResult, RiskAuditResult, RiskLevel

# ---------------------------------------------------------------------------
# Risk-level emoji helpers
# ---------------------------------------------------------------------------

_RISK_EMOJI: dict[str, str] = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
_RISK_BADGE: dict[str, str] = {
    "Low": "![Low](https://img.shields.io/badge/Risk-Low-green)",
    "Medium": "![Medium](https://img.shields.io/badge/Risk-Medium-yellow)",
    "High": "![High](https://img.shields.io/badge/Risk-High-red)",
}


def _risk_emoji(level: RiskLevel) -> str:
    return _RISK_EMOJI.get(level, "⚪")


# ---------------------------------------------------------------------------
# ContractReport
# ---------------------------------------------------------------------------


class ContractReport(BaseModel):
    """
    Full analytical report for a single contract document.

    Combines:
    - Clause extraction results
    - Risk audit results
    - Negotiation recommendations
    - Grounding verification results
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    document_name: str = Field(
        ...,
        min_length=1,
        description="Name or filename of the analysed document.",
    )
    analysis_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp when the analysis was performed.",
    )
    clause_extraction: ClauseExtractionResult = Field(
        ...,
        description="Results from the clause-extraction agent.",
    )
    risk_audit: RiskAuditResult = Field(
        ...,
        description="Results from the risk-audit agent.",
    )
    negotiation_advice: NegotiationResult = Field(
        ...,
        description="Negotiation recommendations from the advisor agent.",
    )
    grounding_verification: GroundingResult = Field(
        ...,
        description="Grounding-verification results from the critic agent.",
    )
    overall_summary: str = Field(
        ...,
        min_length=1,
        description="High-level executive summary of all findings.",
    )

    @field_validator("analysis_timestamp", mode="before")
    @classmethod
    def _normalise_timestamp(cls, v: Any) -> str:
        """Accept datetime objects or plain strings."""
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, str) and v.strip():
            return v.strip()
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """Serialise the report to a JSON string."""
        return self.model_dump_json(indent=indent)

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a plain Python dict (JSON-serialisable)."""
        return json.loads(self.to_json())

    def to_markdown(self) -> str:  # noqa: PLR0912
        """
        Generate a comprehensive, human-readable Markdown report.

        Sections
        --------
        1. Header & metadata
        2. Executive summary
        3. Document type & extraction overview
        4. Extracted clauses table
        5. Risk audit overview
        6. Per-clause risk details
        7. Negotiation recommendations
        8. Grounding verification
        9. Disclaimer
        """
        ra = self.risk_audit
        ce = self.clause_extraction
        na = self.negotiation_advice
        gv = self.grounding_verification

        lines: list[str] = []

        # ── 1. Header ──────────────────────────────────────────────────
        lines += [
            "# 📋 ClauseGuard AI — Contract Analysis Report",
            "",
            f"**Document:** {self.document_name}  ",
            f"**Analysed:** {self.analysis_timestamp}  ",
            f"**Document Type:** {ce.document_type}  ",
            f"**Overall Risk:** {_risk_emoji(ra.overall_risk_level)} **{ra.overall_risk_level}**",
            "",
            "---",
            "",
        ]

        # ── 2. Executive Summary ───────────────────────────────────────
        lines += [
            "## 📝 Executive Summary",
            "",
            self.overall_summary,
            "",
            "---",
            "",
        ]

        # ── 3. Clause Extraction Overview ─────────────────────────────
        lines += [
            "## 🔍 Clause Extraction Overview",
            "",
            f"- **Clauses found:** {ce.total_found}",
            f"- **Document type:** {ce.document_type}",
        ]
        if ce.extraction_notes:
            lines.append(f"- **Notes:** {ce.extraction_notes}")
        lines += ["", ""]

        # ── 4. Extracted Clauses Table ─────────────────────────────────
        if ce.clauses:
            lines += [
                "### Extracted Clauses",
                "",
                "| # | Type | Title | Page | Present | Summary |",
                "|---|------|-------|------|---------|---------|",
            ]
            for i, clause in enumerate(ce.clauses, 1):
                present = "✅" if clause.is_present else "❌"
                summary = clause.summary.replace("|", "\\|").replace("\n", " ")
                lines.append(
                    f"| {i} | `{clause.clause_type}` | {clause.title} "
                    f"| {clause.page_number} | {present} | {summary} |"
                )
            lines += ["", ""]

        # ── 5. Risk Audit Overview ─────────────────────────────────────
        lines += [
            "## ⚠️ Risk Audit",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Overall Risk Level | {_risk_emoji(ra.overall_risk_level)} **{ra.overall_risk_level}** |",
            f"| 🔴 High-risk items | {ra.high_count} |",
            f"| 🟡 Medium-risk items | {ra.medium_count} |",
            f"| 🟢 Low-risk items | {ra.low_count} |",
            "",
            f"**Audit Summary:** {ra.audit_summary}",
            "",
        ]

        # ── 6. Per-clause Risk Details ─────────────────────────────────
        if ra.risk_items:
            lines += ["### Risk Items (sorted by severity)", ""]
            for item in ra.sorted_by_risk():
                emoji = _risk_emoji(item.risk_level)
                lines += [
                    f"#### {emoji} {item.title} (`{item.clause_type}`) — Score: {item.risk_score}/10",
                    "",
                    f"**Risk Level:** {item.risk_level}  ",
                    f"**Page:** {item.page_number}  ",
                    f"**Recommended Action:** {item.recommended_action}",
                    "",
                ]
                if item.concerns:
                    lines.append("**Concerns:**")
                    for concern in item.concerns:
                        if not concern.startswith("[auto-note]"):
                            lines.append(f"- {concern}")
                    lines.append("")
                if item.checklist:
                    lines.append("**Checklist:**")
                    for check_name, flagged in item.checklist.items():
                        flag_icon = "⚠️" if flagged else "✅"
                        lines.append(f"- {flag_icon} {check_name}")
                    lines.append("")
                lines += [
                    "<details>",
                    "<summary>Original clause text</summary>",
                    "",
                    f"> {item.original_text}",
                    "",
                    "</details>",
                    "",
                ]

        lines += ["---", ""]

        # ── 7. Negotiation Recommendations ────────────────────────────
        lines += [
            "## 🤝 Negotiation Recommendations",
            "",
            f"**Strategy:** {na.executive_summary}",
            "",
        ]
        if na.points:
            for pt in na.sorted_by_priority():
                emoji = _risk_emoji(pt.priority)
                lines += [
                    f"### {emoji} {pt.title} (`{pt.clause_type}`) — Priority: {pt.priority}",
                    "",
                    f"**Why it matters:** {pt.explanation}",
                    "",
                    f"**Suggested wording:**",
                    "",
                    f"> {pt.alternative_wording}",
                    "",
                ]
                if pt.negotiation_tips:
                    lines.append("**Negotiation tips:**")
                    for tip in pt.negotiation_tips:
                        lines.append(f"- {tip}")
                    lines.append("")

        lines += ["---", ""]

        # ── 8. Grounding Verification ──────────────────────────────────
        grounded_icon = "✅" if gv.overall_grounded else "⚠️"
        lines += [
            "## 🔗 Grounding Verification",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Overall grounded | {grounded_icon} {'Yes' if gv.overall_grounded else 'No'} |",
            f"| Grounded checks | {gv.grounded_count} |",
            f"| Ungrounded checks | {gv.ungrounded_count} |",
            "",
            f"**Summary:** {gv.grounding_summary}",
            "",
        ]
        ungrounded = gv.ungrounded_checks()
        if ungrounded:
            lines += ["**⚠️ Ungrounded items (requires manual review):**", ""]
            for chk in ungrounded:
                lines += [
                    f"- **{chk.clause_type}** (page {chk.page_number}) — "
                    f"confidence {chk.confidence:.0%}",
                    f"  - Notes: {chk.notes or 'None'}",
                ]
            lines.append("")

        lines += ["---", ""]

        # ── 9. Disclaimer ──────────────────────────────────────────────
        lines += [
            "> ⚠️ **Disclaimer:** ClauseGuard AI provides AI-assisted analysis for "
            "informational purposes only. It does **not** constitute professional legal "
            "advice. Always consult a qualified legal professional before making decisions "
            "based on this analysis.",
            "",
            "_Generated by ClauseGuard AI_",
        ]

        return "\n".join(lines)
