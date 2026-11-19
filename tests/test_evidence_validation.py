"""
tests/test_evidence_validation.py
=================================
Pytest tests for evidence validation and quotation grounding in ClauseGuard AI.
Verifies that extracted clauses are rigorously checked against original document text.
"""

from agents.offline_engine import verify_grounding_offline
from schemas.clause_schema import ClauseExtractionResult, ExtractedClause


class TestEvidenceValidation:
    def test_exact_verbatim_grounding_confirmed(self):
        full_text = (
            "This Agreement is entered into on October 1st. "
            "Either party may terminate this agreement by giving thirty (30) days prior written notice. "
            "All disputes shall be settled in Wilmington, Delaware."
        )
        chunks = [{"text": full_text, "page": 1}]

        clause = ExtractedClause(
            clause_type="notice_period",
            title="Notice Period",
            original_text="Either party may terminate this agreement by giving thirty (30) days prior written notice.",
            page_number=1,
            summary="30 days notice.",
            is_present=True,
        )

        extraction_result = ClauseExtractionResult(
            document_type="Employment Agreement",
            clauses=[clause],
            missing_clause_types=[],
            raw_llm_response="",
        )

        res = verify_grounding_offline(extraction_result, full_text, chunks)
        assert res.overall_grounded is True
        assert len(res.checks) == 1
        assert res.checks[0].is_grounded is True
        assert res.checks[0].confidence == 1.0
        assert res.checks[0].page_number == 1

    def test_fuzzy_token_overlap_grounding(self):
        full_text = (
            "Section 4: The employee agrees to pay back training costs of $5,000 if leaving within two years."
        )
        chunks = [{"text": full_text, "page": 2}]

        # Slightly paraphrased or whitespace-differing quote
        clause = ExtractedClause(
            clause_type="service_bond",
            title="Service Bond",
            original_text="Employee agrees to pay back training costs of $5,000 if leaving within two years.",
            page_number=2,
            summary="Training cost payback.",
            is_present=True,
        )

        extraction_result = ClauseExtractionResult(
            document_type="Employment Agreement",
            clauses=[clause],
            missing_clause_types=[],
            raw_llm_response="",
        )

        res = verify_grounding_offline(extraction_result, full_text, chunks)
        assert res.checks[0].is_grounded is True
        assert res.checks[0].confidence >= 0.70

    def test_hallucinated_text_rejected(self):
        full_text = "This is a simple rental agreement for an apartment."
        chunks = [{"text": full_text, "page": 1}]

        # Fabricated quote not in document
        clause = ExtractedClause(
            clause_type="exit_penalty",
            title="Exit Penalty",
            original_text="The contractor shall pay liquidated damages of one million dollars upon breach.",
            page_number=1,
            summary="Fabricated penalty clause.",
            is_present=True,
        )

        extraction_result = ClauseExtractionResult(
            document_type="Rental Agreement",
            clauses=[clause],
            missing_clause_types=[],
            raw_llm_response="",
        )

        res = verify_grounding_offline(extraction_result, full_text, chunks)
        assert res.checks[0].is_grounded is False
        assert res.checks[0].confidence < 0.40
        assert res.overall_grounded is False
