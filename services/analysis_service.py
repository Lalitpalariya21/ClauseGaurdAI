"""
services/analysis_service.py
============================
Orchestrates the full contract-analysis pipeline:
load PDF → clean text → chunk with page metadata → build vector index
→ retrieve relevant seed chunks → run multi-agent LangGraph workflow
→ return ContractAnalysisState
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Optional, Union

import config.settings as settings
from graph.state import ContractAnalysisState
from graph.workflow import run_analysis
from ingestion.chunker import chunk_pages, get_full_text
from ingestion.pdf_loader import load_pdf
from ingestion.text_cleaner import clean_pages, clean_text
from rag.retriever import Retriever

logger = logging.getLogger(__name__)


class AnalysisService:
    """Owns document ingestion, retrieval caching, and agent pipeline execution."""

    def __init__(self) -> None:
        self._retriever: Optional[Retriever] = None
        self._last_chunks: List[dict] = []
        self._last_pages: List[dict] = []

    @property
    def retriever(self) -> Optional[Retriever]:
        return self._retriever

    def process_document(
        self,
        source: Union[str, Path, bytes],
        document_name: str = "contract.pdf",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        offline: bool = False,
    ) -> ContractAnalysisState:
        """Run the end-to-end contract analysis pipeline."""
        logger.info("AnalysisService: processing '%s' (offline=%s)", document_name, offline)

        # 1. Load PDF
        pages = load_pdf(source)
        self._last_pages = pages
        logger.debug("Loaded %d pages from %s", len(pages), document_name)

        # 2. Clean per-page text
        cleaned_pages = clean_pages(pages)
        full_text = get_full_text(cleaned_pages)
        if not full_text.strip():
            full_text = clean_text("\n\n".join(p.get("text", "") for p in pages))

        # 3. Chunk with page tracking
        chunks = chunk_pages(
            cleaned_pages,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )
        self._last_chunks = chunks
        logger.debug("Generated %d chunks from %d pages.", len(chunks), len(pages))

        # 4. Build Vector Index
        self._retriever = Retriever(chunks=chunks)

        # 5. Retrieve seed chunks for key legal concepts
        seed_query = (
            "notice period service bond termination exit penalty confidentiality "
            "IP ownership auto-renewal payment terms non-compete governing law"
        )
        retrieved_chunks = self._retriever.retrieve(seed_query, top_k=settings.FAISS_TOP_K)

        # 6. Execute Multi-Agent Workflow
        state = run_analysis(
            full_text=full_text,
            chunks=chunks,
            retrieved_chunks=retrieved_chunks,
            document_name=document_name,
            api_key=api_key,
            model=model,
            offline=offline,
        )

        logger.info("AnalysisService: completed analysis for '%s'", document_name)
        return state

    def get_risk_summary(self, state: ContractAnalysisState) -> dict:
        """Extract high-level risk statistics from completed state."""
        summary = {
            "total_clauses": 0,
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
            "overall_risk_level": "Unknown",
            "top_risks": [],
            "error": state.get("error"),
        }

        risk_result: Optional[dict] = state.get("risk_result")
        if not risk_result:
            return summary

        risk_items: List[dict] = risk_result.get("risk_items", [])
        summary["total_clauses"] = len(risk_items)
        summary["overall_risk_level"] = risk_result.get("overall_risk_level", "Unknown")

        high, medium, low = [], [], []
        for item in risk_items:
            level = (item.get("risk_level") or "").capitalize()
            if level == "High":
                high.append(item)
            elif level == "Medium":
                medium.append(item)
            else:
                low.append(item)

        summary["high_risk"] = len(high)
        summary["medium_risk"] = len(medium)
        summary["low_risk"] = len(low)
        summary["top_risks"] = high + medium[:2]

        return summary
