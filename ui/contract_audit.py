"""
ui/contract_audit.py
====================
Main Contract Audit tab for ClauseGuard AI.
Handles PDF upload, sample contract selection, mode switching (Offline vs Groq),
pipeline progress display, and dashboard rendering.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from config.settings import SAMPLE_CONTRACTS
from services.analysis_service import AnalysisService
from services.qa_service import QAService
from ui.components import render_disclaimer
from ui.dashboard import render_dashboard

_ANALYSIS_STEPS = [
    ("📄 Reading & validating PDF…", 0.15),
    ("🧹 Cleaning text and extracting page segments…", 0.30),
    ("🗂️ Building vector embeddings & search index…", 0.45),
    ("🤖 Clause Extractor Agent: identifying legal provisions…", 0.60),
    ("⚠️ Risk Auditor Agent: auditing terms against checklist…", 0.75),
    ("🤝 Negotiation Advisor Agent: drafting alternative wording…", 0.88),
    ("🔎 Grounding Critic Agent: verifying quotations…", 0.98),
    ("📊 Analysis complete!", 1.00),
]


def render_contract_audit(api_key: str = "", model: str = "") -> None:
    """Render the Contract Audit tab."""
    render_disclaimer()

    st.markdown("## 📋 Contract Audit & Risk Analysis")
    st.markdown(
        "Upload any agreement (Employment, Rental, Freelance, NDA) or select a sample contract. "
        "ClauseGuard AI will extract clauses, audit legal risks, suggest counter-wording, "
        "and verify text authenticity."
    )

    # ── Mode Selection Banner ──────────────────────────────────────────────────
    mode_col1, mode_col2 = st.columns([2, 1])
    with mode_col1:
        engine_mode = st.radio(
            "🧠 Select Analysis Engine",
            options=[
                "🛡️ Offline AI Engine (No API key needed — instant, private & deterministic)",
                "⚡ Groq Cloud LLM (Uses Groq API for generative inference)",
            ],
            index=0 if not api_key else 0,
            help="Choose between the built-in local legal intelligence engine and Groq Cloud LLM.",
        )
    with mode_col2:
        is_offline = "Offline AI Engine" in engine_mode
        if is_offline:
            st.success("🟢 **Offline Mode Active:** Zero API calls required. Runs entirely on your machine.", icon="🔒")
        else:
            if api_key:
                st.success(f"⚡ **Groq Mode Active:** Model: `{model}`", icon="🚀")
            else:
                st.warning("⚠️ Enter a Groq API Key in the sidebar to use Groq Cloud mode, or stay in Offline Mode.", icon="🔑")

    st.divider()

    # ── Document Selection ─────────────────────────────────────────────────────
    col_upload, col_sample = st.columns([1, 1])

    with col_upload:
        st.markdown("#### 📂 Option A: Upload Contract")
        uploaded_file = st.file_uploader(
            "Choose a PDF document",
            type=["pdf"],
            help="Supports contracts up to 25 MB.",
        )

    with col_sample:
        st.markdown("#### 📄 Option B: Try Fictional Sample")
        sample_options = ["— None —"] + list(SAMPLE_CONTRACTS.keys())
        selected_sample = st.selectbox(
            "Choose a pre-loaded sample agreement",
            options=sample_options,
            index=0,
            help="Fictional sample contracts designed to showcase diverse clause risks.",
        )

    # Resolve active document source
    source: Any = None
    source_name = ""

    if uploaded_file is not None:
        source = uploaded_file.read()
        source_name = uploaded_file.name
    elif selected_sample and selected_sample != "— None —":
        sample_path = SAMPLE_CONTRACTS.get(selected_sample, "")
        if sample_path and Path(sample_path).exists():
            source = sample_path
            source_name = f"{selected_sample}.pdf"
        else:
            st.warning(f"Sample contract `{selected_sample}` file not found on disk.")

    st.markdown("---")

    # ── Analyse Action Button ──────────────────────────────────────────────────
    analyse_col, info_col = st.columns([1, 2])
    with analyse_col:
        analyse_clicked = st.button(
            "🔍 Start Contract Audit",
            type="primary",
            use_container_width=True,
            disabled=(source is None),
        )
    with info_col:
        if source is not None:
            st.info(f"Ready to analyse: **{source_name}**")
        else:
            st.caption("Upload a PDF file or choose a sample to activate analysis.")

    # ── Execution with Live Progress ───────────────────────────────────────────
    if analyse_clicked and source is not None:
        service = AnalysisService()
        progress_bar = st.progress(0.0, text="Initializing pipeline…")
        status_box = st.empty()

        try:
            for step_name, frac in _ANALYSIS_STEPS[:-2]:
                progress_bar.progress(frac, text=step_name)
                status_box.info(step_name)
                time.sleep(0.15)

            # Actual analysis execution
            actual_offline = is_offline or not api_key
            result_state = service.process_document(
                source=source,
                document_name=source_name,
                api_key=api_key,
                model=model,
                offline=actual_offline,
            )

            # Store in session state
            st.session_state["analysis_state"] = result_state
            st.session_state["document_loaded"] = True
            st.session_state["current_file_name"] = source_name

            # Initialize QA Service for Document Chat
            if service.retriever:
                st.session_state["qa_service"] = QAService(
                    retriever=service.retriever,
                    api_key=api_key,
                    model=model,
                )

            progress_bar.progress(1.0, text="✅ Audit complete!")
            status_box.success(f"Audit completed successfully for **{source_name}**!")
            time.sleep(0.4)
            progress_bar.empty()
            status_box.empty()

        except Exception as exc:
            progress_bar.empty()
            status_box.empty()
            st.error(f"❌ Analysis failed: {exc}")
            return

    # ── Render Results Dashboard ──────────────────────────────────────────────
    if st.session_state.get("analysis_state"):
        state = st.session_state["analysis_state"]
        st.markdown(f"### 📑 Analysis Results: `{st.session_state.get('current_file_name', 'Document')}`")
        render_dashboard(state)
