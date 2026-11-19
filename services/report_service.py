"""
services/report_service.py
==========================
Assembles, formats, and exports ContractReport objects.
Supported formats:
  * Markdown — comprehensive formatted audit report
  * PDF      — styled document via ReportLab
  * JSON     — structured export for machine consumption
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from graph.state import ContractAnalysisState
from schemas.clause_schema import ClauseExtractionResult
from schemas.report_schema import ContractReport
from schemas.risk_schema import GroundingResult, NegotiationResult, RiskAuditResult

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False


class ReportService:
    """Generates contract analysis reports in Markdown, PDF, and JSON formats."""

    def build_report(self, state: ContractAnalysisState) -> ContractReport:
        """Assemble a ContractReport from completed state dict."""
        extraction_dict = state.get("extraction_result") or {}
        risk_dict = state.get("risk_result") or {}
        negotiation_dict = state.get("negotiation_result") or {}
        grounding_dict = state.get("grounding_result") or {}

        try:
            extraction_res = ClauseExtractionResult.model_validate(extraction_dict)
        except Exception:
            extraction_res = ClauseExtractionResult(
                document_type="Contract", clauses=[], missing_clause_types=[], raw_llm_response=""
            )

        try:
            risk_res = RiskAuditResult.model_validate(risk_dict)
        except Exception:
            risk_res = RiskAuditResult(
                risk_items=[], overall_risk_level="Low", high_count=0, medium_count=0, low_count=0, audit_summary=""
            )

        try:
            negotiation_res = NegotiationResult.model_validate(negotiation_dict)
        except Exception:
            negotiation_res = NegotiationResult(points=[], executive_summary="")

        try:
            grounding_res = GroundingResult.model_validate(grounding_dict)
        except Exception:
            grounding_res = GroundingResult(
                checks=[], overall_grounded=False, grounded_count=0, ungrounded_count=0, grounding_summary=""
            )

        overall = risk_res.audit_summary or "Contract analysis completed."

        return ContractReport(
            document_name=state.get("document_name", "contract.pdf"),
            clause_extraction=extraction_res,
            risk_audit=risk_res,
            negotiation_advice=negotiation_res,
            grounding_verification=grounding_res,
            overall_summary=overall,
        )

    def generate_markdown(self, report: ContractReport) -> str:
        """Generate formatted Markdown report."""
        lines = [
            f"# ⚖️ Contract Audit Report: {report.document_name}",
            f"**Generated:** {report.analysis_timestamp}",
            f"**Overall Risk Rating:** {report.risk_audit.overall_risk_level.upper()}",
            "",
            "## 📌 Executive Summary",
            report.overall_summary,
            "",
            "## 📊 Risk Scorecard",
            f"- **🔴 High Risk Clauses:** {report.risk_audit.high_count}",
            f"- **🟠 Medium Risk Clauses:** {report.risk_audit.medium_count}",
            f"- **🟢 Low Risk Clauses:** {report.risk_audit.low_count}",
            f"- **📋 Total Clauses Audited:** {len(report.clause_extraction.clauses)}",
            f"- **🔍 Grounding Authenticity:** {report.grounding_verification.grounding_summary}",
            "",
            "---",
            "",
            "## ⚠️ Detailed Risk Findings & Recommendations",
            "",
        ]

        # Map negotiation points by clause type
        neg_map = {p.clause_type: p for p in report.negotiation_advice.points}

        for item in report.risk_audit.risk_items:
            icon = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(item.risk_level, "⚪")
            lines.append(f"### {icon} {item.title} ({item.risk_level} Risk - Score: {item.risk_score}/10)")
            lines.append(f"**Source:** Page {item.page_number}")
            lines.append("")
            lines.append(f"> **Original Clause:**\n> \"{item.original_text}\"")
            lines.append("")

            if item.concerns:
                lines.append("**Key Concerns:**")
                for c in item.concerns:
                    lines.append(f"- {c}")
                lines.append("")

            lines.append(f"**Recommended Action:** {item.recommended_action}")
            lines.append("")

            # Negotiation suggestion if present
            neg = neg_map.get(item.clause_type)
            if neg:
                lines.append(f"**Plain-English Explanation:** {neg.explanation}")
                lines.append("")
                lines.append("**Suggested Counter-Wording:**")
                lines.append(f"```text\n{neg.alternative_wording}\n```")
                lines.append("")
                if neg.negotiation_tips:
                    lines.append("**Negotiation Tips:**")
                    for tip in neg.negotiation_tips:
                        lines.append(f"- {tip}")
                    lines.append("")

            lines.append("---")
            lines.append("")

        lines.append("## 🔍 Grounding & Authenticity Verification")
        lines.append("| Clause | Page | Verified | Confidence | Notes |")
        lines.append("|---|---|---|---|---|")
        for check in report.grounding_verification.checks:
            status = "✅ Grounded" if check.is_grounded else "❌ Ungrounded"
            conf = f"{int(check.confidence * 100)}%"
            lines.append(f"| {check.clause_type} | {check.page_number} | {status} | {conf} | {check.notes} |")

        lines.append("")
        lines.append("---")
        lines.append(
            "_Disclaimer: This analysis was generated with AI assistance for informational purposes only "
            "and does not constitute formal legal advice._"
        )

        return "\n".join(lines)

    def generate_json(self, report: ContractReport) -> str:
        """Export full structured report in JSON format."""
        return report.model_dump_json(indent=2)

    def generate_pdf_bytes(self, report: ContractReport) -> bytes:
        """Render a clean, formatted PDF report using ReportLab."""
        if not _REPORTLAB_AVAILABLE:
            return self.generate_markdown(report).encode("utf-8")

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E293B"),
            spaceAfter=8,
        )
        h2_style = ParagraphStyle(
            "H2Style",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#334155"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1E293B"),
        )
        quote_style = ParagraphStyle(
            "QuoteStyle",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#475569"),
            leftIndent=10,
        )

        story = []

        # Title
        story.append(Paragraph(f"<b>ClauseGuard AI — Contract Audit Report</b>", title_style))
        story.append(Paragraph(f"<b>Document:</b> {report.document_name} &nbsp;|&nbsp; <b>Risk Rating:</b> {report.risk_audit.overall_risk_level}", body_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10))

        # Executive Summary
        story.append(Paragraph("<b>Executive Summary</b>", h2_style))
        story.append(Paragraph(report.overall_summary, body_style))
        story.append(Spacer(1, 8))

        # Risk Summary Table
        table_data = [
            ["Metric", "Count / Value"],
            ["High Risk Clauses", str(report.risk_audit.high_count)],
            ["Medium Risk Clauses", str(report.risk_audit.medium_count)],
            ["Low Risk Clauses", str(report.risk_audit.low_count)],
            ["Total Clauses", str(len(report.clause_extraction.clauses))],
            ["Grounding Verification", report.grounding_verification.grounding_summary],
        ]
        t = Table(table_data, colWidths=[200, 320])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 12))

        # Key findings
        story.append(Paragraph("<b>Clause Findings & Recommended Action</b>", h2_style))

        for item in report.risk_audit.risk_items:
            risk_color = "#DC2626" if item.risk_level == "High" else ("#EA580C" if item.risk_level == "Medium" else "#16A34A")
            story.append(
                Paragraph(
                    f"<b>{item.title}</b> — <font color='{risk_color}'><b>{item.risk_level} Risk (Score: {item.risk_score}/10)</b></font> (Page {item.page_number})",
                    body_style,
                )
            )
            story.append(Paragraph(f"<i>Original: \"{item.original_text[:280]}...\"</i>", quote_style))
            story.append(Paragraph(f"<b>Action:</b> {item.recommended_action}", body_style))
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=8))
        story.append(
            Paragraph(
                "<font color='#64748B'><i>Disclaimer: Generated for informational purposes only by ClauseGuard AI. Not formal legal advice.</i></font>",
                body_style,
            )
        )

        doc.build(story)
        return buf.getvalue()
