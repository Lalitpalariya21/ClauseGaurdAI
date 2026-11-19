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
    """Render an expander card for a single extracted clause.

    Expected keys in *clause*:
        title (str), clause_type (str), original_text (str),
        summary (str), page_number (int)
    """
    title = clause.get("title", "Untitled Clause")
    clause_type = clause.get("clause_type", "Unknown")
    original_text = clause.get("original_text", "")
    summary = clause.get("summary", "")
    page_number = clause.get("page_number", 0)

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
    """Render an expander card for a single risk item.

    Expected keys in *risk_item*:
        clause_title (str), risk_level (str), concerns (list[str]),
        checklist (list[dict] with keys 'item' and 'status'),
        recommended_action (str)
    """
    clause_title = risk_item.get("clause_title", "Unknown Clause")
    risk_level = risk_item.get("risk_level", "Low")
    concerns = risk_item.get("concerns", [])
    checklist = risk_item.get("checklist", [])
    recommended_action = risk_item.get("recommended_action", "")

    icon = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(risk_level, "⚪")

    with st.expander(f"{icon} {clause_title}", expanded=(risk_level == "High")):
        render_risk_badge(risk_level)
        st.markdown("")

        if concerns:
            st.markdown("**⚠️ Concerns**")
            for concern in concerns:
                st.markdown(f"- {concern}")

        if checklist:
            st.markdown("**✅ Checklist**")
            import pandas as pd  # local import to avoid top-level overhead
            df = pd.DataFrame(checklist)
            if "status" in df.columns:
                df["status"] = df["status"].apply(
                    lambda s: "✅" if str(s).lower() in ("ok", "pass", "✅", "true") else "❌"
                )
            st.table(df)

        if recommended_action:
            st.markdown("**💡 Recommended Action**")
            st.success(recommended_action)


# ── Negotiation Card ──────────────────────────────────────────────────────────

def render_negotiation_card(point: dict) -> None:
    """Render an expander card for a negotiation point.

    Expected keys in *point*:
        clause_title (str), explanation (str),
        alternative_wording (str), negotiation_tips (list[str])
    """
    clause_title = point.get("clause_title", "Clause")
    explanation = point.get("explanation", "")
    alternative_wording = point.get("alternative_wording", "")
    tips = point.get("negotiation_tips", [])

    with st.expander(f"🤝 {clause_title}", expanded=False):
        if explanation:
            st.markdown("**📖 Plain English Explanation**")
            st.write(explanation)

        if alternative_wording:
            st.markdown("**✏️ Suggested Alternative Wording**")
            st.code(alternative_wording, language="text")

        if tips:
            st.markdown("**💬 Negotiation Tips**")
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
    """Render a status card for a single agent execution trace entry.

    Expected keys in *trace_item*:
        agent_name (str), status (str: 'success'|'error'|'running'),
        timestamp (str), output_summary (str)
    """
    agent_name = trace_item.get("agent_name", "Unknown Agent")
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
        f'<span style="font-weight:700;font-size:0.95rem;">🤖 {agent_name}</span>'
        f'<span style="font-size:1.1rem;">{status_icon}</span>'
        f'</div>'
        f'<div style="color:#94a3b8;font-size:0.75rem;margin-top:2px;">🕒 {timestamp}</div>'
        f'<div style="margin-top:8px;font-size:0.85rem;color:#cbd5e1;">{output_summary}</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
