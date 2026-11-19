"""
graph/workflow.py
-----------------
LangGraph StateGraph workflow for ClauseGuard AI.

Pipeline:
START → extract_clauses → audit_risks → advise_negotiation → verify_grounding → END
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from agents.clause_extractor import ClauseExtractorAgent
from agents.grounding_critic import GroundingCriticAgent
from agents.negotiation_advisor import NegotiationAdvisorAgent
from agents.risk_auditor import RiskAuditorAgent
from graph.state import ContractAnalysisState
from schemas.clause_schema import ClauseExtractionResult
from schemas.risk_schema import GroundingResult, NegotiationResult, RiskAuditResult

# Shared agent instances
_clause_extractor = ClauseExtractorAgent()
_risk_auditor = RiskAuditorAgent()
_negotiation_advisor = NegotiationAdvisorAgent()
_grounding_critic = GroundingCriticAgent()


def _now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _append_trace(
    state: ContractAnalysisState,
    agent: str,
    status: str,
    output_summary: str,
) -> None:
    """Append an entry to state['agent_trace']."""
    if "agent_trace" not in state or state["agent_trace"] is None:
        state["agent_trace"] = []
    state["agent_trace"].append(
        {
            "agent": agent,
            "status": status,
            "timestamp": _now_iso(),
            "output_summary": output_summary,
        }
    )


def _accumulate_error(state: ContractAnalysisState, message: str) -> None:
    prior = state.get("error") or ""
    state["error"] = (prior + "\n" + message).strip()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def extract_clauses(state: ContractAnalysisState) -> ContractAnalysisState:
    """Node 1 — ClauseExtractorAgent."""
    agent_name = "ClauseExtractorAgent"
    try:
        retrieved = state.get("retrieved_chunks") or []
        full_text = state.get("full_text", "")
        api_key = state.get("api_key")
        model = state.get("model")
        offline = state.get("offline", False)

        result: ClauseExtractionResult = _clause_extractor.run(
            full_text=full_text,
            retrieved_chunks=retrieved,
            api_key=api_key,
            model=model,
            offline=offline,
        )

        state["extraction_result"] = result.model_dump()
        clause_count = len(result.clauses)
        mode_label = "Offline Engine" if (offline or not api_key) else f"Groq ({model})"
        summary = f"Extracted {clause_count} clause(s) using {mode_label}."
        _append_trace(state, agent_name, "success", summary)

    except Exception:
        err_msg = f"[{agent_name}] {traceback.format_exc()}"
        _accumulate_error(state, err_msg)
        state["extraction_result"] = None
        _append_trace(state, agent_name, "error", f"Agent failed: {traceback.format_exc(limit=1)}")

    return state


def audit_risks(state: ContractAnalysisState) -> ContractAnalysisState:
    """Node 2 — RiskAuditorAgent."""
    agent_name = "RiskAuditorAgent"
    try:
        extraction_dict = state.get("extraction_result")
        if not extraction_dict:
            raise ValueError("extraction_result is empty; skipping risk audit.")

        api_key = state.get("api_key")
        model = state.get("model")
        offline = state.get("offline", False)

        extraction_result = ClauseExtractionResult.model_validate(extraction_dict)
        result: RiskAuditResult = _risk_auditor.run(
            extraction_result=extraction_result,
            api_key=api_key,
            model=model,
            offline=offline,
        )

        state["risk_result"] = result.model_dump()
        high_count = sum(1 for r in result.risk_items if r.risk_level == "High")
        total_items = len(result.risk_items)
        summary = (
            f"Risk audit complete. Found {high_count} high-risk clause(s) "
            f"out of {total_items} identified clauses. Overall Risk: {result.overall_risk_level}."
        )
        _append_trace(state, agent_name, "success", summary)

    except Exception:
        err_msg = f"[{agent_name}] {traceback.format_exc()}"
        _accumulate_error(state, err_msg)
        state["risk_result"] = None
        _append_trace(state, agent_name, "error", f"Agent failed: {traceback.format_exc(limit=1)}")

    return state


def advise_negotiation(state: ContractAnalysisState) -> ContractAnalysisState:
    """Node 3 — NegotiationAdvisorAgent."""
    agent_name = "NegotiationAdvisorAgent"
    try:
        risk_dict = state.get("risk_result")
        extraction_dict = state.get("extraction_result")
        api_key = state.get("api_key")
        model = state.get("model")
        offline = state.get("offline", False)

        if not risk_dict or not extraction_dict:
            raise ValueError("Prior results missing; skipping negotiation advisor.")

        risk_result = RiskAuditResult.model_validate(risk_dict)
        extraction_result = ClauseExtractionResult.model_validate(extraction_dict)

        result: NegotiationResult = _negotiation_advisor.run(
            extraction_result=extraction_result,
            risk_result=risk_result,
            api_key=api_key,
            model=model,
            offline=offline,
        )

        state["negotiation_result"] = result.model_dump()
        point_count = len(result.points)
        summary = f"Generated {point_count} tactical negotiation recommendation(s) and redline alternatives."
        _append_trace(state, agent_name, "success", summary)

    except Exception:
        err_msg = f"[{agent_name}] {traceback.format_exc()}"
        _accumulate_error(state, err_msg)
        state["negotiation_result"] = None
        _append_trace(state, agent_name, "error", f"Agent failed: {traceback.format_exc(limit=1)}")

    return state


def verify_grounding(state: ContractAnalysisState) -> ContractAnalysisState:
    """Node 4 — GroundingCriticAgent."""
    agent_name = "GroundingCriticAgent"
    try:
        extraction_dict = state.get("extraction_result")
        full_text = state.get("full_text", "")
        chunks = state.get("chunks", [])
        api_key = state.get("api_key")
        model = state.get("model")
        offline = state.get("offline", False)

        if not extraction_dict:
            raise ValueError("extraction_result is empty; skipping grounding critic.")

        extraction_result = ClauseExtractionResult.model_validate(extraction_dict)
        result: GroundingResult = _grounding_critic.run(
            extraction_result=extraction_result,
            full_text=full_text,
            chunks=chunks,
            api_key=api_key,
            model=model,
            offline=offline,
        )

        state["grounding_result"] = result.model_dump()
        verified = sum(1 for c in result.checks if c.is_grounded)
        total = len(result.checks)
        summary = f"Grounding check: {verified}/{total} clause quotations verified against original PDF text."
        _append_trace(state, agent_name, "success", summary)

    except Exception:
        err_msg = f"[{agent_name}] {traceback.format_exc()}"
        _accumulate_error(state, err_msg)
        state["grounding_result"] = None
        _append_trace(state, agent_name, "error", f"Agent failed: {traceback.format_exc(limit=1)}")

    return state


# ---------------------------------------------------------------------------
# Workflow Runner
# ---------------------------------------------------------------------------

def _run_sequential(state: ContractAnalysisState) -> ContractAnalysisState:
    """Sequential fallback in case LangGraph is unavailable."""
    state = extract_clauses(state)
    state = audit_risks(state)
    state = advise_negotiation(state)
    state = verify_grounding(state)
    return state


def run_analysis(
    full_text: str,
    chunks: list[dict],
    retrieved_chunks: list[dict],
    document_name: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    offline: bool = False,
) -> ContractAnalysisState:
    """Run the complete multi-agent contract analysis workflow."""
    initial_state: ContractAnalysisState = {
        "full_text": full_text,
        "chunks": chunks,
        "retrieved_chunks": retrieved_chunks,
        "extraction_result": None,
        "risk_result": None,
        "negotiation_result": None,
        "grounding_result": None,
        "agent_trace": [],
        "error": None,
        "document_name": document_name,
        "api_key": api_key,
        "model": model,
        "offline": offline,
    }

    try:
        from langgraph.graph import END, START, StateGraph

        builder = StateGraph(ContractAnalysisState)
        builder.add_node("extract_clauses", extract_clauses)
        builder.add_node("audit_risks", audit_risks)
        builder.add_node("advise_negotiation", advise_negotiation)
        builder.add_node("verify_grounding", verify_grounding)

        builder.add_edge(START, "extract_clauses")
        builder.add_edge("extract_clauses", "audit_risks")
        builder.add_edge("audit_risks", "advise_negotiation")
        builder.add_edge("advise_negotiation", "verify_grounding")
        builder.add_edge("verify_grounding", END)

        graph = builder.compile()
        return graph.invoke(initial_state)
    except Exception as exc:
        # Fallback to sequential pipeline execution
        return _run_sequential(initial_state)


def get_agent_trace(state: ContractAnalysisState) -> list[dict]:
    return state.get("agent_trace") or []
