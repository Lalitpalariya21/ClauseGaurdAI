"""
ClauseGuard AI — Risk audit, negotiation, and grounding schemas (Pydantic v2).

Defines the data structures produced by the risk-auditor, negotiation-advisor,
and grounding-critic agents.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Shared literals
# ---------------------------------------------------------------------------

RiskLevel = Literal["Low", "Medium", "High"]

RISK_ORDER: dict[str, int] = {"Low": 0, "Medium": 1, "High": 2}


# ---------------------------------------------------------------------------
# RiskItem
# ---------------------------------------------------------------------------


class RiskItem(BaseModel):
    """Risk assessment for a single identified clause."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    clause_type: str = Field(
        ...,
        min_length=1,
        description="Clause type label (matches ClauseType values).",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Human-readable clause title.",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Qualitative risk rating: Low / Medium / High.",
    )
    risk_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Numerical risk score from 1 (safest) to 10 (most risky).",
    )
    concerns: list[str] = Field(
        default_factory=list,
        description="Bullet-point concerns identified in this clause.",
    )
    checklist: dict[str, bool] = Field(
        default_factory=dict,
        description="Named risk-checklist items and whether each is flagged.",
    )
    recommended_action: str = Field(
        ...,
        min_length=1,
        description="Concise recommended action for the job-seeker / contractor.",
    )
    original_text: str = Field(
        ...,
        min_length=1,
        description="Verbatim clause text this risk item relates to.",
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="1-based page number of the clause in the source document.",
    )

    @field_validator("concerns", mode="before")
    @classmethod
    def _ensure_concerns_list(cls, v: object) -> object:
        if isinstance(v, str):
            return [v]
        return v

    @model_validator(mode="after")
    def _validate_score_vs_level(self) -> "RiskItem":
        """Soft-validate that risk_score is roughly consistent with risk_level."""
        mapping: dict[str, range] = {
            "Low": range(1, 5),
            "Medium": range(4, 8),
            "High": range(7, 11),
        }
        expected_range = mapping[self.risk_level]
        if self.risk_score not in expected_range:
            note = (
                f"[auto-note] risk_score={self.risk_score} may be inconsistent "
                f"with risk_level='{self.risk_level}'."
            )
            if note not in self.concerns:
                self.concerns.append(note)
        return self


# ---------------------------------------------------------------------------
# RiskAuditResult
# ---------------------------------------------------------------------------


class RiskAuditResult(BaseModel):
    """Aggregated risk-audit report covering all clauses in a document."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    risk_items: list[RiskItem] = Field(
        default_factory=list,
        description="Per-clause risk items.",
    )
    overall_risk_level: RiskLevel = Field(
        ...,
        description="Highest risk level seen across all items.",
    )
    high_count: int = Field(..., ge=0, description="Number of High-risk items.")
    medium_count: int = Field(..., ge=0, description="Number of Medium-risk items.")
    low_count: int = Field(..., ge=0, description="Number of Low-risk items.")
    audit_summary: str = Field(
        ...,
        min_length=1,
        description="Executive summary of the overall risk audit.",
    )

    @model_validator(mode="after")
    def _sync_counts(self) -> "RiskAuditResult":
        """Auto-correct counts if they don't match the actual items list."""
        high = sum(1 for r in self.risk_items if r.risk_level == "High")
        medium = sum(1 for r in self.risk_items if r.risk_level == "Medium")
        low = sum(1 for r in self.risk_items if r.risk_level == "Low")
        object.__setattr__(self, "high_count", high)
        object.__setattr__(self, "medium_count", medium)
        object.__setattr__(self, "low_count", low)
        if self.risk_items:
            max_level = max(
                self.risk_items, key=lambda r: RISK_ORDER[r.risk_level]
            ).risk_level
            object.__setattr__(self, "overall_risk_level", max_level)
        return self

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def items_by_level(self, level: RiskLevel) -> list[RiskItem]:
        return [r for r in self.risk_items if r.risk_level == level]

    def sorted_by_risk(self) -> list[RiskItem]:
        return sorted(
            self.risk_items,
            key=lambda r: (-RISK_ORDER[r.risk_level], -r.risk_score),
        )


# ---------------------------------------------------------------------------
# NegotiationPoint
# ---------------------------------------------------------------------------


class NegotiationPoint(BaseModel):
    """A single negotiation recommendation for a problematic clause."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    clause_type: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=256)
    explanation: str = Field(
        ...,
        min_length=1,
        description="Plain-English explanation of why this clause is concerning.",
    )
    alternative_wording: str = Field(
        ...,
        min_length=1,
        description="Suggested replacement or amendment wording.",
    )
    negotiation_tips: list[str] = Field(
        default_factory=list,
        description="Actionable negotiation tips for the reader.",
    )
    priority: RiskLevel = Field(
        ...,
        description="Priority level for addressing this negotiation point.",
    )

    @field_validator("negotiation_tips", mode="before")
    @classmethod
    def _ensure_tips_list(cls, v: object) -> object:
        if isinstance(v, str):
            return [v]
        return v


# ---------------------------------------------------------------------------
# NegotiationResult
# ---------------------------------------------------------------------------


class NegotiationResult(BaseModel):
    """Full negotiation advice for a document."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    points: list[NegotiationPoint] = Field(
        default_factory=list,
        description="Individual negotiation points, ordered by priority.",
    )
    executive_summary: str = Field(
        ...,
        min_length=1,
        description="High-level negotiation strategy summary.",
    )

    def high_priority_points(self) -> list[NegotiationPoint]:
        return [p for p in self.points if p.priority == "High"]

    def sorted_by_priority(self) -> list[NegotiationPoint]:
        return sorted(self.points, key=lambda p: -RISK_ORDER[p.priority])


# ---------------------------------------------------------------------------
# GroundingCheck
# ---------------------------------------------------------------------------


class GroundingCheck(BaseModel):
    """Verification of whether a quoted clause text exists in the source document."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    clause_type: str = Field(..., min_length=1)
    original_text: str = Field(
        ...,
        min_length=1,
        description="The clause text that was checked against the source.",
    )
    is_grounded: bool = Field(
        ...,
        description="True if the text was found verbatim or near-verbatim in the source.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0–1.0) that the grounding verdict is correct.",
    )
    evidence_snippet: str = Field(
        default="",
        description="Matching snippet from the source document that supports the verdict.",
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="Page number where evidence was found (or expected to be).",
    )
    notes: str = Field(
        default="",
        description="Free-form notes from the grounding agent.",
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v: object) -> float:
        """Accept string representations like '0.85'."""
        return float(v)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# GroundingResult
# ---------------------------------------------------------------------------


class GroundingResult(BaseModel):
    """Aggregated grounding-verification result for a document."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    checks: list[GroundingCheck] = Field(
        default_factory=list,
        description="Per-clause grounding checks.",
    )
    overall_grounded: bool = Field(
        ...,
        description="True if all checks passed grounding verification.",
    )
    grounded_count: int = Field(..., ge=0)
    ungrounded_count: int = Field(..., ge=0)
    grounding_summary: str = Field(
        ...,
        min_length=1,
        description="Summary of the grounding verification run.",
    )

    @model_validator(mode="after")
    def _sync_counts(self) -> "GroundingResult":
        grounded = sum(1 for c in self.checks if c.is_grounded)
        ungrounded = len(self.checks) - grounded
        object.__setattr__(self, "grounded_count", grounded)
        object.__setattr__(self, "ungrounded_count", ungrounded)
        object.__setattr__(self, "overall_grounded", (ungrounded == 0 and len(self.checks) > 0))
        return self

    def ungrounded_checks(self) -> list[GroundingCheck]:
        return [c for c in self.checks if not c.is_grounded]
