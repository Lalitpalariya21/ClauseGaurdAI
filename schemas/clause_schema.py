"""
ClauseGuard AI — Clause extraction schemas (Pydantic v2).

Defines the data structures produced by the clause-extraction agent.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# ClauseType
# ---------------------------------------------------------------------------

ClauseType = Literal[
    "notice_period",
    "service_bond",
    "termination",
    "exit_penalty",
    "confidentiality",
    "ip_ownership",
    "auto_renewal",
    "payment_terms",
    "non_compete",
    "governing_law",
    "other",
]

VALID_CLAUSE_TYPES: tuple[str, ...] = (
    "notice_period",
    "service_bond",
    "termination",
    "exit_penalty",
    "confidentiality",
    "ip_ownership",
    "auto_renewal",
    "payment_terms",
    "non_compete",
    "governing_law",
    "other",
)


# ---------------------------------------------------------------------------
# ExtractedClause
# ---------------------------------------------------------------------------


class ExtractedClause(BaseModel):
    """A single clause identified inside a contract document."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    clause_type: ClauseType = Field(
        ...,
        description="Canonical type label for this clause.",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Short human-readable title for the clause.",
    )
    original_text: str = Field(
        ...,
        min_length=1,
        description="Verbatim text of the clause as it appears in the document.",
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="1-based page number where the clause was found.",
    )
    summary: str = Field(
        ...,
        min_length=1,
        description="Plain-English one-to-three sentence summary of the clause.",
    )
    is_present: bool = Field(
        ...,
        description="True if the clause was actually found in the document.",
    )

    @field_validator("original_text", mode="before")
    @classmethod
    def _strip_original_text(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("summary", mode="before")
    @classmethod
    def _strip_summary(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


# ---------------------------------------------------------------------------
# ClauseExtractionResult
# ---------------------------------------------------------------------------


class ClauseExtractionResult(BaseModel):
    """Aggregated result of running clause extraction over an entire document."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    clauses: list[ExtractedClause] = Field(
        default_factory=list,
        description="All clauses extracted from the document.",
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total number of clauses found (should equal len(clauses)).",
    )
    document_type: str = Field(
        ...,
        min_length=1,
        description="Inferred document type, e.g. 'Employment Contract', 'NDA'.",
    )
    extraction_notes: str = Field(
        default="",
        description="Free-form notes from the extraction agent (warnings, caveats, etc.).",
    )
    missing_clause_types: list[str] = Field(
        default_factory=list,
        description="Types of clauses not detected in the document.",
    )
    raw_llm_response: str = Field(
        default="",
        description="Raw response output from the LLM or engine.",
    )

    @model_validator(mode="after")
    def _sync_total_found(self) -> "ClauseExtractionResult":
        """Keep total_found consistent with the actual list length."""
        object.__setattr__(self, "total_found", len(self.clauses))
        return self

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def by_type(self, clause_type: ClauseType) -> list[ExtractedClause]:
        """Return all clauses of a given type."""
        return [c for c in self.clauses if c.clause_type == clause_type]

    def present_clauses(self) -> list[ExtractedClause]:
        """Return only clauses that were actually found (is_present=True)."""
        return [c for c in self.clauses if c.is_present]
