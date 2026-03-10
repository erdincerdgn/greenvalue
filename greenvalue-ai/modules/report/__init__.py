"""
GreenValue AI — IVS-2025-Compliant Report Generation Module

Generates professional PDF reports that comply with International Valuation
Standards (IVS) January 2025.  Reports are accepted by banks, appraisal boards,
and institutional investors.

Architecture (v2):
    PDFRenderer         — Jinja2 + HTML/CSS + WeasyPrint  (design = HTML only)
    ChainOfThought      — LangGraph stateful workflow + Pydantic structured outputs
                          (isolated micro-agents, zero hallucination)

Components:
    ReportEngine        — Main orchestrator (build → render → store)
    IVSTemplate         — IVS-2025 section structure & compliance rules
    SectionGenerator    — Individual report section builders
    ChartRenderer       — Energy gauge, ROI waterfall, heatmap overlay
    PDFRenderer         — Jinja2 + WeasyPrint HTML→PDF rendering
    ChainOfThought      — LangGraph multi-book reasoning (Physics → Cost → Finance → Appraisal)

Usage:
    from modules.report import ReportEngine, ReportConfig, ChainOfThoughtEngine

    chain = ChainOfThoughtEngine(rag_pipeline=rag, llm=llm)
    engine = ReportEngine(chain_engine=chain)
    result = await engine.generate(
        property_id="abc-123",
        analysis_result=vision_analysis,
        config=ReportConfig(report_type=ReportType.FULL_IVS),
    )
    pdf_bytes = result.pdf_bytes
"""

from .engine import ReportEngine, ReportConfig, ReportResult, ReportType
from .ivs_template import IVSTemplate, IVSSection, IVSReportData
from .chain_of_thought import (
    ChainOfThoughtEngine, ChainStep, ChainResult, ChainRole,
    # v2: Pydantic structured output models
    PhysicsOutput, CostOutput, FinanceOutput, AppraisalOutput,
    WorkflowState,
)
from .sections import SectionGenerator
from .charts import ChartRenderer
from .pdf_renderer import PDFRenderer

__all__ = [
    "ReportEngine", "ReportConfig", "ReportResult", "ReportType",
    "IVSTemplate", "IVSSection", "IVSReportData",
    "ChainOfThoughtEngine", "ChainStep", "ChainResult", "ChainRole",
    "PhysicsOutput", "CostOutput", "FinanceOutput", "AppraisalOutput",
    "WorkflowState",
    "SectionGenerator", "ChartRenderer", "PDFRenderer",
]
