"""
ui/dashboard.py
===============
Interactive Risk Analysis Dashboard for ClauseGuard AI.
Provides risk distribution metrics, interactive filters, side-by-side risk & rewrite cards.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

from ui.components import (
    render_metrics_row,
    render_negotiation_card,
    render_risk_card,
)


def render_dashboard(state: dict) -> None:
    """Render the full interactive contract risk dashboard."""
    risk_result = state.get("risk_result") or {}
    negotiation_result = state.get("negotiation_result") or {}
    extraction_result = state.get("extraction_result") or {}

    risk_items: List[dict] = risk_result.get("risk_items", [])
    negotiation_points: List[dict] = negotiation_result.get("points", [])
    clauses: List[dict] = extraction_result.get("clauses", [])

    if not risk_items and not clauses:
        st.info("No clause data available. Please upload a contract and click Analyse.")
        return

    high_items = [i for i in risk_items if i.get("risk_level") == "High"]
    medium_items = [i for i in risk_items if i.get("risk_level") == "Medium"]
    low_items = [i for i in risk_items if i.get("risk_level") == "Low"]

    # ── Summary Metrics ────────────────────────────────────────────────────────
    st.markdown("### 📊 Contract Risk Overview")
    render_metrics_row(
        high=len(high_items),
        medium=len(medium_items),
        low=len(low_items),
        total=len(risk_items) if risk_items else len(clauses),
    )

    if risk_result.get("audit_summary"):
        st.info(f"💡 **Executive Summary:** {risk_result.get('audit_summary')}")

    # ── Risk Distribution Chart & Quick Stats ──────────────────────────────────
    chart_col, stat_col = st.columns([2, 1])
    with chart_col:
        chart_df = pd.DataFrame(
            {
                "Risk Level": ["🔴 High", "🟠 Medium", "🟢 Low"],
                "Count": [len(high_items), len(medium_items), len(low_items)],
            }
        ).set_index("Risk Level")
        st.bar_chart(chart_df, height=180, use_container_width=True)

    with stat_col:
        st.markdown("#### 🛡️ Health Score")
        total_clauses = max(1, len(risk_items))
        health_score = max(0, 100 - (len(high_items) * 30 + len(medium_items) * 12))
        score_color = "#22c55e" if health_score >= 75 else ("#f59e0b" if health_score >= 50 else "#ef4444")
        st.markdown(
            f"""
            <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:15px;text-align:center;">
                <span style="font-size:2.4rem;font-weight:800;color:{score_color};">{health_score}/100</span><br>
                <span style="font-size:0.85rem;color:#94a3b8;">Contract Safety Index</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Interactive Filter Controls ────────────────────────────────────────────
    st.markdown("### 🔍 Filter Audited Clauses")
    col_filter_risk, col_search = st.columns([1, 2])

    with col_filter_risk:
        risk_filter = st.selectbox(
            "Filter by Risk Level",
            options=["All Risks", "🔴 High Risk Only", "🟠 Medium Risk Only", "🟢 Low Risk Only"],
            index=0,
        )

    with col_search:
        search_query = st.text_input(
            "Search Clause Title or Keywords",
            placeholder="e.g. notice, bond, termination, IP...",
        )

    # Filter clauses
    filtered_items = list(risk_items)
    if risk_filter == "🔴 High Risk Only":
        filtered_items = [i for i in filtered_items if i.get("risk_level") == "High"]
    elif risk_filter == "🟠 Medium Risk Only":
        filtered_items = [i for i in filtered_items if i.get("risk_level") == "Medium"]
    elif risk_filter == "🟢 Low Risk Only":
        filtered_items = [i for i in filtered_items if i.get("risk_level") == "Low"]

    if search_query.strip():
        sq = search_query.lower()
        filtered_items = [
            i for i in filtered_items
            if sq in i.get("title", "").lower()
            or sq in i.get("clause_type", "").lower()
            or sq in i.get("original_text", "").lower()
        ]

    st.caption(f"Showing **{len(filtered_items)}** of **{len(risk_items)}** clauses")

    # Map negotiation points by clause_type
    neg_lookup = {p.get("clause_type"): p for p in negotiation_points}

    # ── Render Clause Cards ───────────────────────────────────────────────────
    if not filtered_items:
        st.warning("No clauses match the selected filters.")
        return

    for item in filtered_items:
        c_type = item.get("clause_type")
        neg_point = neg_lookup.get(c_type)

        left_col, right_col = st.columns(2)
        with left_col:
            render_risk_card(item)
        with right_col:
            if neg_point:
                render_negotiation_card(neg_point)
            else:
                st.info("No counter-negotiation points required for this clause.")
