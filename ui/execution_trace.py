"""
ui/execution_trace.py
=====================
Agent Execution Trace & Report Export tab for ClauseGuard AI.
Displays LangGraph agent pipeline execution logs, Pydantic structured schemas,
grounding verification table, and report downloads (Markdown, PDF, JSON).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.report_service import ReportService
from ui.components import render_agent_status_card


def render_execution_trace() -> None:
    """Render the Agent Execution Trace and Report Downloads tab."""
    st.markdown("## 🔍 Agent Execution Trace & Report Export")
    st.markdown(
        "Inspect the multi-agent LangGraph workflow execution, review structured Pydantic schemas, "
        "and export comprehensive contract audit reports."
    )

    state = st.session_state.get("analysis_state")

    if not state:
        st.info("👆 Run a contract analysis in the **Contract Audit** tab to inspect agent traces.")
        return

    doc_name = state.get("document_name", "contract.pdf")

    # ── Report Export Buttons ──────────────────────────────────────────────────
    st.markdown("### 📥 Download Contract Audit Report")
    report_service = ReportService()

    try:
        contract_report = report_service.build_report(state)
        md_text = report_service.generate_markdown(contract_report)
        json_text = report_service.generate_json(contract_report)
        pdf_bytes = report_service.generate_pdf_bytes(contract_report)

        col_md, col_pdf, col_json = st.columns(3)

        with col_md:
            st.download_button(
                label="📝 Download Markdown (.md)",
                data=md_text,
                file_name=f"ClauseGuard_Audit_{doc_name}.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with col_pdf:
            st.download_button(
                label="📄 Download PDF Report (.pdf)",
                data=pdf_bytes,
                file_name=f"ClauseGuard_Audit_{doc_name}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with col_json:
            st.download_button(
                label="📦 Export Structured JSON (.json)",
                data=json_text,
                file_name=f"ClauseGuard_Audit_{doc_name}.json",
                mime="application/json",
                use_container_width=True,
            )
    except Exception as exc:
        st.error(f"Error preparing report downloads: {exc}")

    st.divider()

    # ── LangGraph Multi-Agent Pipeline Visualization ───────────────────────────
    st.markdown("### 🤖 Multi-Agent LangGraph Workflow")
    st.markdown(
        """
        <div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:16px;text-align:center;margin-bottom:15px;">
            <div style="display:flex;justify-content:space-around;align-items:center;flex-wrap:wrap;gap:8px;">
                <span style="background:#3b82f6;color:white;padding:6px 14px;border-radius:8px;font-weight:600;font-size:0.85rem;">
                    1. Clause Extractor
                </span>
                <span style="color:#64748b;font-weight:bold;">➔</span>
                <span style="background:#f97316;color:white;padding:6px 14px;border-radius:8px;font-weight:600;font-size:0.85rem;">
                    2. Risk Auditor
                </span>
                <span style="color:#64748b;font-weight:bold;">➔</span>
                <span style="background:#8b5cf6;color:white;padding:6px 14px;border-radius:8px;font-weight:600;font-size:0.85rem;">
                    3. Negotiation Advisor
                </span>
                <span style="color:#64748b;font-weight:bold;">➔</span>
                <span style="background:#10b981;color:white;padding:6px 14px;border-radius:8px;font-weight:600;font-size:0.85rem;">
                    4. Grounding Critic
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Execution Trace Cards ─────────────────────────────────────────────────
    st.markdown("#### ⏱️ Agent Execution Trace Logs")
    trace_items = state.get("agent_trace") or []

    if trace_items:
        for t in trace_items:
            # Map keys to components render expectations
            item = {
                "agent_name": t.get("agent", "Agent"),
                "status": t.get("status", "success"),
                "timestamp": t.get("timestamp", ""),
                "output_summary": t.get("output_summary", ""),
            }
            render_agent_status_card(item)
    else:
        st.info("No trace events recorded.")

    st.divider()

    # ── Grounding Verification Scorecard ───────────────────────────────────────
    st.markdown("### 🔎 Grounding Verification Results")
    grounding_result = state.get("grounding_result") or {}
    checks = grounding_result.get("checks", [])

    if checks:
        st.caption(f"Status: **{grounding_result.get('grounding_summary', '')}**")
        table_rows = []
        for c in checks:
            status_symbol = "✅ Grounded" if c.get("is_grounded") else "❌ Ungrounded"
            conf = f"{int(c.get('confidence', 0.0) * 100)}%"
            table_rows.append(
                {
                    "Clause Type": c.get("clause_type"),
                    "Source Page": c.get("page_number", 1),
                    "Verification": status_symbol,
                    "Confidence": conf,
                    "Evidence / Notes": c.get("notes") or c.get("evidence_snippet", "")[:120],
                }
            )
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
    else:
        st.info("No grounding checks available.")

    st.divider()

    # ── Structured Pydantic Output Inspector ──────────────────────────────────
    st.markdown("### 📜 Structured Pydantic Output Explorer")
    t1, t2, t3, t4 = st.tabs(
        [
            "📋 Clause Extraction",
            "⚠️ Risk Audit",
            "🤝 Negotiation Advice",
            "🔍 Grounding Critic",
        ]
    )

    with t1:
        st.json(state.get("extraction_result") or {})

    with t2:
        st.json(state.get("risk_result") or {})

    with t3:
        st.json(state.get("negotiation_result") or {})

    with t4:
        st.json(state.get("grounding_result") or {})
