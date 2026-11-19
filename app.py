"""
ClauseGuard AI — Main Streamlit Entry Point
AI-Assisted Contract Analysis & Risk Identification System
"""

import streamlit as st

# ── Page config must be first Streamlit call ───────────────────────────
st.set_page_config(
    page_title="ClauseGuard AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import os
from pathlib import Path

from config.settings import (
    APP_SUBTITLE,
    APP_TITLE,
    DEFAULT_MODEL,
    DISCLAIMER,
    GROQ_API_KEY,
    SAMPLE_CONTRACTS,
)
from ui.contract_audit import render_contract_audit
from ui.document_chat import render_document_chat
from ui.execution_trace import render_execution_trace

# ── Available Groq models ──────────────────────────────────────────────
AVAILABLE_MODELS = [
    "openai/gpt-oss-20b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
]


def init_session_state() -> None:
    """Initialise all required session-state keys."""
    defaults: dict = {
        "analysis_state": None,
        "qa_service": None,
        "chat_history": [],
        "document_loaded": False,
        "pdf_pages": [],
        "chunks": [],
        "current_file_name": None,
        "api_key_override": "",
        "selected_model": DEFAULT_MODEL,
        "use_offline_mode": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> tuple[str, str]:
    """
    Render sidebar and return (api_key, selected_model).
    """
    with st.sidebar:
        # ── Logo / Title ───────────────────────────────────────────────
        st.markdown(
            """
            <div style="text-align:center; padding: 0.8rem 0 0.5rem 0;">
                <span style="font-size:3rem;">⚖️</span>
                <h2 style="margin:0; color:#F1F5F9; font-weight:800;">ClauseGuard AI</h2>
                <p style="margin:0; font-size:0.8rem; color:#94A3B8;">
                    AI-Assisted Contract Analysis & Risk Auditor
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        # Check effective API key
        env_key = GROQ_API_KEY
        sidebar_key = st.session_state.get("api_key_override", "")

        # ── Optional Groq LLM Settings Expander ───────────────────────
        with st.expander("⚙️ Optional Groq Cloud LLM", expanded=bool(sidebar_key or env_key)):
            st.caption("Default is the built-in Zero-API engine. Enter a Groq key here only if you wish to use cloud generative models.")
            entered_key = st.text_input(
                "Groq API Key",
                type="password",
                value=sidebar_key,
                placeholder="gsk_...",
                help="Optional. Leave blank to run 100% locally with zero API calls.",
            )
            if entered_key:
                st.session_state["api_key_override"] = entered_key
                effective_key = entered_key
            elif env_key:
                effective_key = env_key
            else:
                effective_key = ""

            selected_model = st.selectbox(
                "Groq Model",
                options=AVAILABLE_MODELS,
                index=0,
            )
            st.session_state["selected_model"] = selected_model

        if effective_key:
            st.success(f"⚡ Groq Cloud Active (`{selected_model}`)", icon="🚀")
        else:
            effective_key = ""
            selected_model = DEFAULT_MODEL
            st.info("🛡️ **Zero-API Engine Active**\n\nRuns privately on your device. No API keys needed.", icon="🔒")

        st.divider()

        # ── About ──────────────────────────────────────────────────────
        with st.expander("ℹ️ About ClauseGuard AI", expanded=False):
            st.markdown(
                """
                **ClauseGuard AI** empowers non-lawyers to review complex agreements:
                - 📋 **Clause Extraction:** identifies notice periods, bonds, IP ownership, termination, etc.
                - ⚠️ **Risk Scorecard:** rates clauses Low / Medium / High with explainable checklists.
                - 🤝 **Negotiation Advisor:** translates legal jargon into plain English & counter-wording.
                - 🔍 **Grounding Critic:** mathematically verifies quotations against original PDF pages.
                - 💬 **Ask Your Document:** RAG Q&A with exact page citations.
                """
            )

        st.divider()
        st.markdown(DISCLAIMER)

    return effective_key, selected_model


def main() -> None:
    init_session_state()

    # ── Sidebar ────────────────────────────────────────────────────────
    api_key, selected_model = render_sidebar()

    # ── Main header ────────────────────────────────────────────────────
    col_title, col_badge = st.columns([3.5, 1.5])
    with col_title:
        st.title(f"⚖️ {APP_TITLE}")
        st.caption(APP_SUBTITLE)
    with col_badge:
        if api_key:
            st.markdown(
                f"""
                <div style="background:#1e293b;border:1px solid #3b82f6;border-radius:8px;padding:8px 12px;text-align:center;margin-top:10px;">
                    <span style="color:#3b82f6;font-weight:bold;font-size:0.85rem;">⚡ Groq Ready</span><br>
                    <span style="color:#94a3b8;font-size:0.75rem;">{selected_model}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background:#1e293b;border:1px solid #22c55e;border-radius:8px;padding:8px 12px;text-align:center;margin-top:10px;">
                    <span style="color:#22c55e;font-weight:bold;font-size:0.85rem;">🛡️ Zero-API Engine Ready</span><br>
                    <span style="color:#94a3b8;font-size:0.75rem;">100% Free & Private</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_audit, tab_chat, tab_trace = st.tabs(
        ["📋 Contract Audit", "💬 Ask Your Document", "🔍 Agent Execution & Reports"]
    )

    with tab_audit:
        render_contract_audit(api_key=api_key, model=selected_model)

    with tab_chat:
        render_document_chat(api_key=api_key, model=selected_model)

    with tab_trace:
        render_execution_trace()


if __name__ == "__main__":
    main()
