"""ui/components.py — Reusable Streamlit UI components for ClauseGuard AI."""
from __future__ import annotations

import streamlit as st


# ── Disclaimer ────────────────────────────────────────────────────────────────

def render_disclaimer() -> None:
    """Render the legal disclaimer as a Streamlit warning box."""
    st.warning(
        "⚠️ **Disclaimer:** ClauseGuard AI provides AI-assisted analysis for "
        "informational purposes only. It does **not** constitute professional legal "
        "advice. Always consult a qualified legal professional before making decisions "
        "based on this analysis."
    )


# ── Risk Badge ────────────────────────────────────────────────────────────────

_BADGE_STYLES: dict[str, str] = {
    "High":   "background:#ef4444;color:#fff;",
    "Medium": "background:#f97316;color:#fff;",
    "Low":    "background:#22c55e;color:#fff;",
}

def render_risk_badge(risk_level: str) -> None:
    """Render a coloured inline HTML badge for the given risk level."""
    style = _BADGE_STYLES.get(risk_level, "background:#6b7280;color:#fff;")
    badge_html = (
        f'<span style="'
        f'{style}'
        f'padding:3px 10px;border-radius:12px;font-size:0.78rem;'
        f'font-weight:700;letter-spacing:0.04em;">'
        f'{risk_level} Risk</span>'
    )
    st.markdown(badge_html, unsafe_allow_html=True)


# ── Page Reference ────────────────────────────────────────────────────────────

def render_page_reference(page: int) -> None:
    """Render a small styled page-reference indicator."""
    html = (
        f'<span style="font-size:0.75rem;color:#94a3b8;'
        f'border:1px solid #334155;border-radius:6px;padding:2px 7px;">'
        f'📄 Page {page}</span>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Clause Card ───────────────────────────────────────────────────────────────

def render_clause_card(clause: dict) -> None:
    """Render an expander card for a single extracted clause."""
    title = clause.get("title") or clause.get("clause_title", "Untitled Clause")
    clause_type = clause.get("clause_type", "Unknown")
    original_text = clause.get("original_text", "")
    summary = clause.get("summary", "")
    page_number = clause.get("page_number", 1)

    with st.expander(f"📋 {title}", expanded=False):
        col_type, col_page = st.columns([3, 1])
        with col_type:
            st.markdown(
                f'<span style="background:#3b82f6;color:#fff;padding:2px 9px;'
                f'border-radius:10px;font-size:0.76rem;font-weight:600;">'
                f'{clause_type}</span>',
                unsafe_allow_html=True,
            )
        with col_page:
            render_page_reference(page_number)

        st.markdown("**📝 Summary**")
        st.info(summary)

        st.markdown("**🔤 Original Text**")
        st.markdown(
            f'<div style="background:#1e293b;border-left:3px solid #4f46e5;'
            f'padding:10px 14px;border-radius:4px;font-size:0.85rem;'
            f'font-family:monospace;white-space:pre-wrap;">{original_text}</div>',
            unsafe_allow_html=True,
        )


# ── Risk Card ─────────────────────────────────────────────────────────────────

def render_risk_card(risk_item: dict) -> None:
    """Render an expander card for a single risk item."""
    clause_title = risk_item.get("title") or risk_item.get("clause_title", "Contract Clause")
    risk_level = risk_item.get("risk_level", "Low")
    risk_score = risk_item.get("risk_score")
    clause_type = risk_item.get("clause_type", "")
    page_number = risk_item.get("page_number", 1)
    concerns = risk_item.get("concerns", [])
    checklist = risk_item.get("checklist", {})
    recommended_action = risk_item.get("recommended_action", "")
    original_text = risk_item.get("original_text", "")

    icon = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(risk_level, "⚪")

    with st.expander(f"{icon} {clause_title}", expanded=(risk_level == "High")):
        col_badge, col_score, col_page = st.columns([1.5, 1.5, 1])
        with col_badge:
            render_risk_badge(risk_level)
        with col_score:
            if risk_score is not None:
                st.markdown(f"**Risk Score:** `{risk_score}/10`")
        with col_page:
            render_page_reference(page_number)

        st.markdown("")

        if original_text:
            st.markdown("**🔤 Original Quoted Text**")
            st.markdown(
                f'<div style="background:#0f172a;border-left:3px solid #3b82f6;'
                f'padding:8px 12px;border-radius:4px;font-size:0.83rem;'
                f'font-family:monospace;white-space:pre-wrap;color:#e2e8f0;margin-bottom:10px;">{original_text}</div>',
                unsafe_allow_html=True,
            )

        if concerns:
            st.markdown("**⚠️ Identified Concerns**")
            for concern in concerns:
                st.markdown(f"- {concern}")

        if checklist:
            st.markdown("**✅ Risk Checklist Assessment**")
            import pandas as pd
            if isinstance(checklist, dict):
                df = pd.DataFrame([
                    {"Verification Criteria": str(k), "Status": "✅ Pass" if v else "⚠️ Flagged"}
                    for k, v in checklist.items()
                ])
            elif isinstance(checklist, list):
                df = pd.DataFrame(checklist)
                if "status" in df.columns:
                    df["status"] = df["status"].apply(
                        lambda s: "✅ Pass" if str(s).lower() in ("ok", "pass", "✅", "true") else "⚠️ Flagged"
                    )
            else:
                df = pd.DataFrame()
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)

        if recommended_action:
            st.markdown("**💡 Recommended Action**")
            st.success(recommended_action)


# ── Negotiation Card ──────────────────────────────────────────────────────────

def render_negotiation_card(point: dict) -> None:
    """Render an expander card for a negotiation point."""
    clause_title = point.get("title") or point.get("clause_title", "Counter-Proposal")
    priority = point.get("priority", "Medium")
    explanation = point.get("explanation", "")
    alternative_wording = point.get("alternative_wording", "")
    tips = point.get("negotiation_tips", [])

    with st.expander(f"🤝 Counter-Wording: {clause_title}", expanded=(priority == "High")):
        if priority:
            render_risk_badge(priority)
            st.markdown("")

        if explanation:
            st.markdown("**📖 Plain-English Explanation**")
            st.write(explanation)

        if alternative_wording:
            st.markdown("**✏️ Suggested Alternative Wording (Ready to Propose)**")
            st.code(alternative_wording, language="text")

        if tips:
            st.markdown("**💬 Tactical Negotiation Tips**")
            for tip in tips:
                st.markdown(f"- {tip}")


# ── Metrics Row ───────────────────────────────────────────────────────────────

def render_metrics_row(high: int, medium: int, low: int, total: int) -> None:
    """Render a 4-column metrics strip (High / Medium / Low / Total clauses)."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="🔴 High Risk", value=high, delta=None)
    with col2:
        st.metric(label="🟠 Medium Risk", value=medium, delta=None)
    with col3:
        st.metric(label="🟢 Low Risk", value=low, delta=None)
    with col4:
        st.metric(label="📋 Total Clauses", value=total, delta=None)


# ── Agent Status Card ─────────────────────────────────────────────────────────

def render_agent_status_card(trace_item: dict) -> None:
    """Render a status card for a single agent execution trace entry."""
    agent_name = trace_item.get("agent_name") or trace_item.get("agent", "Agent")
    status = trace_item.get("status", "running")
    timestamp = trace_item.get("timestamp", "")
    output_summary = trace_item.get("output_summary", "")

    status_icon = {"success": "✅", "error": "❌", "running": "⏳"}.get(status, "⏳")
    border_color = {"success": "#22c55e", "error": "#ef4444", "running": "#f59e0b"}.get(
        status, "#6b7280"
    )

    card_html = (
        f'<div style="border:1px solid {border_color};border-radius:8px;'
        f'padding:12px 16px;margin-bottom:8px;background:#1e293b;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-weight:700;font-size:0.95rem;color:#f8fafc;">🤖 {agent_name}</span>'
        f'<span style="font-size:1.1rem;">{status_icon}</span>'
        f'</div>'
        f'<div style="color:#94a3b8;font-size:0.75rem;margin-top:2px;">🕒 {timestamp}</div>'
        f'<div style="margin-top:8px;font-size:0.85rem;color:#cbd5e1;">{output_summary}</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
