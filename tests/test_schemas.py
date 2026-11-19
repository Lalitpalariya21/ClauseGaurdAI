"""
tests/test_schemas.py
=====================
Pytest tests for Pydantic v2 schemas across ClauseGuard AI.
Covers Clause schemas, Risk schemas, Negotiation schemas, Grounding schemas, and Report schemas.
"""

import pytest
from pydantic import ValidationError

from schemas.clause_schema import ClauseExtractionResult, ExtractedClause
from schemas.report_schema import ContractReport
from schemas.risk_schema import (
    GroundingCheck,
    GroundingResult,
    NegotiationPoint,
    NegotiationResult,
    RiskAuditResult,
    RiskItem,
)


class TestClauseSchema:
    def test_valid_clause_creation(self):
        clause = ExtractedClause(
            clause_type="notice_period",
            title="Notice Period",
            original_text="Employee must give 30 days notice.",
            page_number=1,
            summary="Standard 30 days notice.",
            is_present=True,
        )
        assert clause.clause_type == "notice_period"
        assert clause.page_number == 1
        assert clause.is_present is True

    def test_invalid_clause_type_raises(self):
        with pytest.raises(ValidationError):
            ExtractedClause(
                clause_type="invalid_clause_type_foo",  # not in Literal
                title="Test",
                original_text="Some text",
                page_number=1,
                summary="Some summary",
                is_present=True,
            )

    def test_page_number_negative_raises(self):
        with pytest.raises(ValidationError):
            ExtractedClause(
                clause_type="notice_period",
                title="Test",
                original_text="Some text",
                page_number=0,  # ge=1
                summary="Some summary",
                is_present=True,
            )

    def test_clause_extraction_result(self):
        result = ClauseExtractionResult(
            document_type="Employment Agreement",
            clauses=[
                ExtractedClause(
                    clause_type="termination",
                    title="Termination",
                    original_text="Either party may terminate.",
                    page_number=2,
                    summary="Mutual termination.",
                    is_present=True,
                )
            ],
            missing_clause_types=["service_bond"],
            raw_llm_response="{}",
        )
        assert result.document_type == "Employment Agreement"
        assert len(result.clauses) == 1
        assert "service_bond" in result.missing_clause_types


class TestRiskSchema:
    def test_valid_risk_item(self):
        item = RiskItem(
            clause_type="service_bond",
            title="Service Bond",
            risk_level="High",
            risk_score=9,
            concerns=["Requires $5000 exit payment."],
            checklist={"Is bond mutual?": False},
            recommended_action="Negotiate deletion.",
            original_text="Employee pays $5,000 on departure.",
            page_number=1,
        )
        assert item.risk_level == "High"
        assert item.risk_score == 9

    def test_risk_audit_result_sync_counts(self):
        item1 = RiskItem(
            clause_type="service_bond",
            title="Service Bond",
            risk_level="High",
            risk_score=8,
            concerns=["Penalty"],
            checklist={},
            recommended_action="Reject",
            original_text="Pay $5000",
            page_number=1,
        )
        item2 = RiskItem(
            clause_type="notice_period",
            title="Notice",
            risk_level="Low",
            risk_score=2,
            concerns=[],
            checklist={},
            recommended_action="Accept",
            original_text="30 days",
            page_number=1,
        )
        audit = RiskAuditResult(
            risk_items=[item1, item2],
            overall_risk_level="Low",  # Should auto-sync to High
            high_count=0,
            medium_count=0,
            low_count=0,
            audit_summary="Summary",
        )
        assert audit.high_count == 1
        assert audit.low_count == 1
        assert audit.overall_risk_level == "High"


class TestGroundingSchema:
    def test_grounding_result_sync(self):
        check1 = GroundingCheck(
            clause_type="notice_period",
            original_text="Notice text",
            is_grounded=True,
            confidence=1.0,
            evidence_snippet="Notice text found",
            page_number=1,
        )
        check2 = GroundingCheck(
            clause_type="service_bond",
            original_text="Bond text",
            is_grounded=False,
            confidence=0.2,
            evidence_snippet="",
            page_number=2,
        )
        res = GroundingResult(
            checks=[check1, check2],
            overall_grounded=True,
            grounded_count=0,
            ungrounded_count=0,
            grounding_summary="Verification completed",
        )
        assert res.grounded_count == 1
        assert res.ungrounded_count == 1
        assert res.overall_grounded is False


class TestReportSchema:
    def test_contract_report_generation(self):
        clause = ExtractedClause(
            clause_type="confidentiality",
            title="Confidentiality",
            original_text="Keep secret.",
            page_number=1,
            summary="Keep secret summary.",
            is_present=True,
        )
        c_res = ClauseExtractionResult(
            document_type="NDA", clauses=[clause], missing_clause_types=[], raw_llm_response=""
        )
        r_res = RiskAuditResult(
            risk_items=[], overall_risk_level="Low", high_count=0, medium_count=0, low_count=0, audit_summary="All safe"
        )
        n_res = NegotiationResult(points=[], executive_summary="No points")
        g_res = GroundingResult(
            checks=[], overall_grounded=True, grounded_count=0, ungrounded_count=0, grounding_summary="All good"
        )

        report = ContractReport(
            document_name="test.pdf",
            clause_extraction=c_res,
            risk_audit=r_res,
            negotiation_advice=n_res,
            grounding_verification=g_res,
            overall_summary="Safe contract",
        )
        assert report.document_name == "test.pdf"
        md = report.to_markdown()
        assert "test.pdf" in md
        assert "CONFIDENTIALITY" in md.upper()
