"""
ui/document_chat.py
===================
Interactive RAG Chatbot tab for ClauseGuard AI.
Answers natural-language questions with evidence citations and page references.
"""

from __future__ import annotations

import streamlit as st

from services.qa_service import QAService
from ui.components import render_page_reference

SUGGESTED_QUESTIONS = [
    "What is the required notice period to resign?",
    "Is there a service bond or minimum tenure penalty?",
    "Who owns the intellectual property and inventions?",
    "Under what conditions can the agreement be terminated?",
    "What are the payment terms, invoicing, and late fees?",
]


def render_document_chat(api_key: str = "", model: str = "") -> None:
    """Render the Ask Your Document RAG chatbot interface."""
    st.markdown("## 💬 Ask Your Document")
    st.markdown(
        "Chat with your contract using Retrieval-Augmented Generation (RAG). "
        "Answers are grounded strictly in the uploaded document with verifiable page citations."
    )

    if not st.session_state.get("document_loaded"):
        st.info("👆 Please upload and analyse a contract in the **Contract Audit** tab first.")
        return

    qa_service: QAService | None = st.session_state.get("qa_service")
    if not qa_service:
        st.warning("Retrieval index is not ready. Please re-run the analysis.")
        return

    file_name = st.session_state.get("current_file_name", "Contract")
    st.caption(f"Currently chatting with: **{file_name}**")

    # ── Quick Question Chips ──────────────────────────────────────────────────
    st.markdown("##### 💡 Suggested Questions")
    chip_cols = st.columns(len(SUGGESTED_QUESTIONS))
    chosen_question = None

    for col, q_text in zip(chip_cols, SUGGESTED_QUESTIONS):
        with col:
            # Short label for button
            short_lbl = q_text.split("?")[0][:25] + "…"
            if st.button(short_lbl, key=f"chip_{q_text}", use_container_width=True, help=q_text):
                chosen_question = q_text

    st.markdown("---")

    # ── Chat History Container ────────────────────────────────────────────────
    chat_container = st.container()

    # Initialize chat history in session state
    if "chat_history" not in st.session_state or st.session_state["chat_history"] is None:
        st.session_state["chat_history"] = []

    # Display chat history
    with chat_container:
        for msg in st.session_state["chat_history"]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            sources = msg.get("sources", [])
            confidence = msg.get("confidence")

            with st.chat_message(role):
                st.markdown(content)
                if sources and role == "assistant":
                    with st.expander("📚 Source Evidence & Citations", expanded=False):
                        if confidence:
                            conf_color = "#22c55e" if confidence == "High" else "#f59e0b"
                            st.markdown(
                                f"**Retrieval Confidence:** <span style='color:{conf_color};font-weight:bold;'>{confidence}</span>",
                                unsafe_allow_html=True,
                            )
                        for s in sources:
                            p_num = s.get("page", 1)
                            snippet = s.get("text", "")
                            render_page_reference(p_num)
                            st.markdown(f"> *\"{snippet}\"*")

    # ── User Input Handling ───────────────────────────────────────────────────
    user_input = st.chat_input("Ask a question about your contract...")
    prompt_to_process = chosen_question or user_input

    if prompt_to_process:
        # Display user message
        st.session_state["chat_history"].append({"role": "user", "content": prompt_to_process})
        with st.chat_message("user"):
            st.markdown(prompt_to_process)

        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Searching document passages…"):
                response = qa_service.answer(
                    question=prompt_to_process,
                    chat_history=st.session_state["chat_history"],
                    api_key=api_key,
                    model=model,
                    offline=(not api_key),
                )
                answer_text = response.get("answer", "No answer found.")
                sources = response.get("sources", [])
                conf = response.get("confidence", "Medium")

                st.markdown(answer_text)
                if sources:
                    with st.expander("📚 Source Evidence & Citations", expanded=True):
                        st.markdown(f"**Confidence:** `{conf}`")
                        for s in sources:
                            render_page_reference(s.get("page", 1))
                            st.markdown(f"> *\"{s.get('text', '')}\"*")

                # Store assistant response in history
                st.session_state["chat_history"].append(
                    {
                        "role": "assistant",
                        "content": answer_text,
                        "sources": sources,
                        "confidence": conf,
                    }
                )

    # ── Chat Controls ─────────────────────────────────────────────────────────
    if st.session_state.get("chat_history"):
        st.markdown("")
        col_clear, _ = st.columns([1, 4])
        with col_clear:
            if st.button("🗑️ Clear Chat History", use_container_width=True):
                st.session_state["chat_history"] = []
                st.rerun()
