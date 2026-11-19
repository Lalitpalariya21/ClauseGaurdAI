"""
graph/state.py
--------------
LangGraph state definition for the ClauseGuard AI contract analysis workflow.
"""

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict


class ContractAnalysisState(TypedDict, total=False):
    """Shared mutable state passed through the LangGraph StateGraph nodes."""

    full_text: str
    chunks: list[dict]
    retrieved_chunks: list[dict]
    extraction_result: Optional[dict]
    risk_result: Optional[dict]
    negotiation_result: Optional[dict]
    grounding_result: Optional[dict]
    agent_trace: list[dict]
    error: Optional[str]
    document_name: str
    api_key: Optional[str]
    model: Optional[str]
    offline: bool
