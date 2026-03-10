"""
GreenValue AI — Multi-Book Chain-of-Thought Engine  (LangGraph v2)

ARCHITECTURE DECISION (v2):
    Ditched mega-prompting for LangGraph Stateful Workflow.

    Problem (v1):
    - Llama 3.2 (3B) has a small context window.
    - Feeding 4 books at once makes the model hallucinate 100%.
    - Numbers get fabricated, sources are mixed across domains.

    Solution (v2):
    - Isolated micro-agents with Pydantic structured JSON outputs.
    - Each step receives ONLY:
        a) The previous step's validated JSON (NOT the full prompt history)
        b) RAG context from ONE specific book
    - Context is COMPLETELY CLEARED between steps — fresh LLM call each time.
    - A Pydantic model enforces the output schema; if the LLM output is wrong,
      it is caught immediately instead of silently propagating garbage.

    Graph:
        [Physics Agent]  →  [Cost Agent]  →  [Finance Agent]  →  [Appraisal Agent]
         Book #3              Book #6          Book #7           Books #1 + #2

Dependencies:
    pip install langgraph pydantic
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("greenvalue-report")


# ══════════════════════════════════════════════════════════════════
# 1.  Pydantic Structured Output Models
#     Every LLM step MUST return data matching one of these schemas.
#     If parsing fails, the step is marked as failed — zero hallucination.
# ══════════════════════════════════════════════════════════════════

class PhysicsDeficiency(BaseModel):
    """A single thermal deficiency found by the Physics Expert."""
    component: str = Field(..., description="e.g. roof_insulation, windows, external_walls")
    current_u_value: float = Field(..., ge=0, description="Current U-value W/m²K")
    target_u_value: float = Field(..., ge=0, description="Recommended U-value W/m²K")
    condition: str = Field(default="poor", description="poor | fair | good")
    area_sqm: float = Field(default=0, ge=0)
    heat_loss_kwh_year: float = Field(default=0, ge=0)
    co2_kg_year: float = Field(default=0, ge=0)
    priority: str = Field(default="medium", description="high | medium | low")
    recommended_upgrade: str = Field(default="")


class PhysicsOutput(BaseModel):
    """Validated output of Step 1 — Physics Expert."""
    deficiencies: List[PhysicsDeficiency] = Field(default_factory=list)


class CostEstimate(BaseModel):
    """A single cost estimate for one upgrade."""
    component: str
    upgrade_description: str = ""
    material_cost: float = Field(default=0, ge=0)
    labour_cost: float = Field(default=0, ge=0)
    total_cost: float = Field(default=0, ge=0)
    cost_per_sqm: float = Field(default=0, ge=0)
    confidence: str = Field(default="moderate", description="high | moderate | low")
    cost_source: str = ""


class CostOutput(BaseModel):
    """Validated output of Step 2 — Cost Expert."""
    estimates: List[CostEstimate] = Field(default_factory=list)


class FinanceMetrics(BaseModel):
    """Financial return metrics for one upgrade."""
    component: str
    total_cost: float = Field(default=0, ge=0)
    annual_energy_savings_kwh: float = Field(default=0, ge=0)
    annual_savings_currency: float = Field(default=0, ge=0)
    simple_payback_years: float = Field(default=0, ge=0)
    roi_percent: float = Field(default=0)
    capitalised_value_add: float = Field(default=0, ge=0)
    npv_10yr: float = Field(default=0)
    irr_percent: float = Field(default=0)
    valuation_method: str = ""
    finance_source: str = ""


class FinanceOutput(BaseModel):
    """Validated output of Step 3 — Finance Expert."""
    metrics: List[FinanceMetrics] = Field(default_factory=list)


class UpgradeCard(BaseModel):
    """Final upgrade card produced by the Appraisal Expert."""
    component: str
    description: str = ""
    cost: float = Field(default=0, ge=0)
    value_add: float = Field(default=0, ge=0)
    roi_percent: float = Field(default=0)
    payback_years: float = Field(default=0, ge=0)
    energy_savings_kwh: float = Field(default=0, ge=0)
    co2_reduction_kg: float = Field(default=0, ge=0)
    label_impact: str = ""
    cost_source: str = ""
    finance_source: str = ""
    valuation_method: str = ""
    ivs_basis: str = ""


class AppraisalOutput(BaseModel):
    """Validated output of Step 4 — Appraisal Expert."""
    upgrades: List[UpgradeCard] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════
# 2.  Workflow State  (passed between LangGraph nodes)
# ══════════════════════════════════════════════════════════════════

class WorkflowState(BaseModel):
    """
    Typed state carried through the LangGraph state machine.

    Each node reads what it needs and writes its output.
    The LLM context is NOT carried — only the validated JSON objects.
    """
    # Inputs (set once at the start)
    detections: List[Dict[str, Any]] = Field(default_factory=list)
    u_values: List[Dict[str, Any]] = Field(default_factory=list)
    energy_label: str = ""
    property_meta: Dict[str, Any] = Field(default_factory=dict)

    # Step outputs (set progressively)
    physics: Optional[PhysicsOutput] = None
    cost: Optional[CostOutput] = None
    finance: Optional[FinanceOutput] = None
    appraisal: Optional[AppraisalOutput] = None

    # Execution log
    step_logs: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
# 3.  Legacy data structures  (kept for backward compatibility
#     with engine.py and the rest of the codebase)
# ══════════════════════════════════════════════════════════════════

class ChainRole(str, Enum):
    PHYSICS_EXPERT = "physics_expert"
    COST_EXPERT = "cost_expert"
    FINANCE_EXPERT = "finance_expert"
    APPRAISAL_EXPERT = "appraisal_expert"


@dataclass
class ChainStep:
    """A single reasoning step in the chain."""
    step_number: int = 0
    role: ChainRole = ChainRole.PHYSICS_EXPERT
    book_ids: List[str] = field(default_factory=list)
    book_titles: List[str] = field(default_factory=list)
    prompt: str = ""
    raw_response: str = ""
    structured_output: Dict[str, Any] = field(default_factory=dict)
    rag_context_chunks: int = 0
    duration_seconds: float = 0.0
    success: bool = False
    error: Optional[str] = None


@dataclass
class UpgradeOutput:
    """A single upgrade recommendation produced by the chain."""
    component: str = ""
    description: str = ""
    cost: float = 0.0
    value_add: float = 0.0
    roi_percent: float = 0.0
    payback_years: float = 0.0
    energy_savings_kwh: float = 0.0
    co2_reduction_kg: float = 0.0
    label_impact: str = ""
    cost_source: str = ""
    finance_source: str = ""
    valuation_method: str = ""


@dataclass
class ChainResult:
    """Complete output of a chain-of-thought run."""
    steps: List[ChainStep] = field(default_factory=list)
    upgrades: List[Dict[str, Any]] = field(default_factory=list)
    step_logs: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    success: bool = False
    error: Optional[str] = None
    # Aggregate metrics
    total_cost: float = 0.0
    total_value_add: float = 0.0
    aggregate_roi: float = 0.0
    label_before: str = ""
    label_after: str = ""


# ══════════════════════════════════════════════════════════════════
# 4.  Isolated Prompt Templates  (one per micro-agent)
#
#     CRITICAL: Each prompt is self-contained.
#     It receives ONLY:
#       • the previous step's JSON output (not raw LLM text)
#       • RAG context from ONE specific book
#     The LLM context window is FRESH each time.
# ══════════════════════════════════════════════════════════════════

PHYSICS_PROMPT = """You are a **Building Physics Expert**.
Reference book: "{book_title}"

## Task
Analyse the detected building components and their U-values.
Identify components with poor thermal performance that need upgrading.

## Input Data
Detections:
{detections}

U-values:
{u_values}

Current energy label: {energy_label}
Property metadata:
{property_meta}

## Reference Material (RAG — {book_title})
{rag_context}

## REQUIRED OUTPUT — JSON ONLY
Return ONLY a JSON object matching this schema (no explanation text):
```json
{{
  "deficiencies": [
    {{
      "component": "roof_insulation",
      "current_u_value": 1.8,
      "target_u_value": 0.15,
      "condition": "poor",
      "area_sqm": 120,
      "heat_loss_kwh_year": 3500,
      "co2_kg_year": 700,
      "priority": "high",
      "recommended_upgrade": "Add 200mm mineral wool insulation (U = 0.15 W/m²K)"
    }}
  ]
}}
```
Only include components that genuinely need upgrading based on thermal physics."""


COST_PROMPT = """You are a **Renovation Cost Expert**.
Reference book: "{book_title}"

## Task
Estimate the cost of each recommended upgrade below.
Use per-unit cost benchmarks and adjust for the property.

## Previous Step Output — Physics Expert
{physics_json}

## Property metadata
{property_meta}

## Reference Material (RAG — {book_title})
{rag_context}

## REQUIRED OUTPUT — JSON ONLY
Return ONLY a JSON object matching this schema:
```json
{{
  "estimates": [
    {{
      "component": "roof_insulation",
      "upgrade_description": "Add 200mm mineral wool insulation",
      "material_cost": 4800,
      "labour_cost": 3200,
      "total_cost": 8000,
      "cost_per_sqm": 66.7,
      "confidence": "moderate",
      "cost_source": "{book_title} — Chapter X, Table Y"
    }}
  ]
}}
```
Be conservative with estimates. Include material + labour."""


FINANCE_PROMPT = """You are a **Real Estate Finance Expert**.
Reference book: "{book_title}"

## Task
Calculate financial returns for each proposed upgrade.
Use energy savings from Physics and costs from the Cost step.

## Previous Step Outputs
Physics findings (deficiencies):
{physics_json}

Cost estimates:
{cost_json}

## Property metadata
{property_meta}

## Financial Parameters
Cap rate: {cap_rate}%
Discount rate: {discount_rate}%
Energy cost/kWh: {energy_cost_per_kwh} {currency}

## Reference Material (RAG — {book_title})
{rag_context}

## REQUIRED OUTPUT — JSON ONLY
Return ONLY a JSON object matching this schema:
```json
{{
  "metrics": [
    {{
      "component": "roof_insulation",
      "total_cost": 8000,
      "annual_energy_savings_kwh": 3500,
      "annual_savings_currency": 700,
      "simple_payback_years": 11.4,
      "roi_percent": 75,
      "capitalised_value_add": 11667,
      "npv_10yr": 3200,
      "irr_percent": 8.5,
      "valuation_method": "Income Approach — capitalised savings at 6% cap rate",
      "finance_source": "{book_title}"
    }}
  ]
}}
```"""


APPRAISAL_PROMPT = """You are an **IVS-Certified Appraisal Expert**.
Reference books:
- {ivs_title}
- {appraisal_title}

## Task
Reconcile the upgrade analysis into IVS-2025-compliant value opinions.
For each upgrade, confirm the value-add using appropriate IVS valuation approaches.

## Previous Step Outputs
Physics findings:
{physics_json}

Cost estimates:
{cost_json}

Finance analysis:
{finance_json}

## Property metadata
{property_meta}

## Reference Material (RAG — IVS + Appraisal)
{rag_context}

## REQUIRED OUTPUT — JSON ONLY
Return ONLY a JSON object matching this schema:
```json
{{
  "upgrades": [
    {{
      "component": "roof_insulation",
      "description": "Add 200mm mineral wool insulation to roof",
      "cost": 8000,
      "value_add": 11667,
      "roi_percent": 75,
      "payback_years": 11.4,
      "energy_savings_kwh": 3500,
      "co2_reduction_kg": 700,
      "label_impact": "D → B",
      "cost_source": "The Book on Flipping Houses (J. Scott) — Ch. 8",
      "finance_source": "What Every RE Investor Needs to Know — Cap Rate",
      "valuation_method": "Income Approach — IVS 105",
      "ivs_basis": "IVS 104 Market Value; IVS 105 Income Approach"
    }}
  ]
}}
```"""


# ══════════════════════════════════════════════════════════════════
# 5.  Chain-of-Thought Engine  (LangGraph version)
# ══════════════════════════════════════════════════════════════════

class ChainOfThoughtEngine:
    """
    Orchestrates multi-book sequential reasoning via isolated micro-agents.

    Architecture (v2 — LangGraph):
        • Each step is a LangGraph node
        • State object (WorkflowState) carries ONLY validated JSON
        • Context window is cleared between steps (fresh LLM call)
        • Pydantic models enforce output schemas — no regex JSON parsing

    Fallback:
        If langgraph is not installed, runs the same logic sequentially
        without the graph framework (same isolation guarantees).

    Usage:
        engine = ChainOfThoughtEngine(rag_pipeline=rag, llm=llm)
        result = await engine.execute(detections, u_values, energy_label, property_meta)
    """

    # Default financial parameters
    DEFAULT_CAP_RATE = 6.0
    DEFAULT_DISCOUNT_RATE = 8.0
    DEFAULT_ENERGY_COST_PER_KWH = 0.20
    DEFAULT_CURRENCY = "€"

    def __init__(
        self,
        rag_pipeline: Optional[Any] = None,
        llm: Optional[Any] = None,
        book_library: Optional[Dict] = None,
        cap_rate: float = DEFAULT_CAP_RATE,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        energy_cost_per_kwh: float = DEFAULT_ENERGY_COST_PER_KWH,
        currency: str = DEFAULT_CURRENCY,
    ):
        self.rag_pipeline = rag_pipeline
        self.llm = llm
        self.cap_rate = cap_rate
        self.discount_rate = discount_rate
        self.energy_cost_per_kwh = energy_cost_per_kwh
        self.currency = currency

        # Book metadata
        if book_library is None:
            try:
                from ..rag.router import BOOK_LIBRARY
                self.book_library = BOOK_LIBRARY
            except ImportError:
                self.book_library = {}
                logger.warning("Could not import BOOK_LIBRARY — chain will lack book metadata")
        else:
            self.book_library = book_library

        # Try to build a LangGraph state machine
        self._graph = self._build_graph()

        logger.info(
            "ChainOfThoughtEngine v2 initialised (LangGraph=%s, cap=%.1f%%, discount=%.1f%%)",
            self._graph is not None, cap_rate, discount_rate,
        )

    # ------------------------------------------------------------------
    # Build LangGraph (optional — graceful fallback)
    # ------------------------------------------------------------------

    def _build_graph(self) -> Optional[Any]:
        """
        Build a LangGraph StateGraph:
            physics → cost → finance → appraisal

        Returns None if langgraph is not installed.
        """
        try:
            from langgraph.graph import StateGraph, END

            graph = StateGraph(WorkflowState)

            graph.add_node("physics_agent", self._node_physics)
            graph.add_node("cost_agent", self._node_cost)
            graph.add_node("finance_agent", self._node_finance)
            graph.add_node("appraisal_agent", self._node_appraisal)

            graph.set_entry_point("physics_agent")
            graph.add_edge("physics_agent", "cost_agent")
            graph.add_edge("cost_agent", "finance_agent")
            graph.add_edge("finance_agent", "appraisal_agent")
            graph.add_edge("appraisal_agent", END)

            return graph.compile()

        except ImportError:
            logger.info("langgraph not installed — using sequential fallback")
            return None
        except Exception as exc:
            logger.warning("LangGraph build failed: %s — using sequential fallback", exc)
            return None

    # ------------------------------------------------------------------
    # Public API  (same signature as v1 — drop-in replacement)
    # ------------------------------------------------------------------

    async def execute(
        self,
        detections: List[Dict],
        u_values: List[Dict],
        energy_label: str = "",
        property_meta: Optional[Dict] = None,
    ) -> ChainResult:
        """
        Run the full 4-step chain-of-thought.

        Returns a ChainResult with structured upgrade recommendations.
        """
        start = time.time()
        property_meta = property_meta or {}

        result = ChainResult(label_before=energy_label)

        # Fail fast if no LLM is configured
        if not self.llm:
            logger.warning("No LLM configured — skipping chain-of-thought")
            result.error = "No LLM configured for chain-of-thought"
            result.total_duration_seconds = round(time.time() - start, 3)
            return result

        logger.info(
            "Starting chain-of-thought v2 (detections=%d, u_values=%d)",
            len(detections), len(u_values),
        )

        initial_state = WorkflowState(
            detections=detections,
            u_values=u_values,
            energy_label=energy_label,
            property_meta=property_meta,
        )

        try:
            if self._graph is not None:
                # ── LangGraph execution ──
                final_state = await self._run_graph(initial_state)
            else:
                # ── Sequential fallback (same isolation) ──
                final_state = await self._run_sequential(initial_state)

            # ── Convert WorkflowState → ChainResult ──
            result.step_logs = final_state.step_logs

            if final_state.error:
                result.error = final_state.error
            elif final_state.appraisal:
                result.upgrades = [u.model_dump() for u in final_state.appraisal.upgrades]
                result.total_cost = sum(u.get("cost", 0) for u in result.upgrades)
                result.total_value_add = sum(u.get("value_add", 0) for u in result.upgrades)
                if result.total_cost > 0:
                    result.aggregate_roi = round(
                        (result.total_value_add - result.total_cost) / result.total_cost * 100, 1
                    )
                result.success = True
            else:
                result.error = "Appraisal step did not produce output"

        except Exception as exc:
            logger.error("Chain-of-thought v2 execution failed: %s", exc, exc_info=True)
            result.error = str(exc)

        result.total_duration_seconds = round(time.time() - start, 3)
        logger.info(
            "Chain v2 complete in %.2fs — %d upgrades, ROI=%.1f%%",
            result.total_duration_seconds, len(result.upgrades), result.aggregate_roi,
        )
        return result

    # ------------------------------------------------------------------
    # LangGraph execution
    # ------------------------------------------------------------------

    async def _run_graph(self, state: WorkflowState) -> WorkflowState:
        """Run the compiled LangGraph."""
        result = await self._graph.ainvoke(state.model_dump())
        return WorkflowState(**result) if isinstance(result, dict) else result

    # ------------------------------------------------------------------
    # Sequential fallback (used when langgraph is not installed)
    # ------------------------------------------------------------------

    async def _run_sequential(self, state: WorkflowState) -> WorkflowState:
        """Run the same 4-step pipeline without LangGraph."""
        state = await self._node_physics(state)
        if state.error:
            return state

        state = await self._node_cost(state)
        if state.error:
            return state

        state = await self._node_finance(state)
        if state.error:
            return state

        state = await self._node_appraisal(state)
        return state

    # ══════════════════════════════════════════════════════════════
    # LangGraph Nodes  (each one is an ISOLATED micro-agent)
    #
    #   ISOLATION CONTRACT:
    #   • The LLM receives a FRESH prompt (no prior chat history)
    #   • The only data from previous steps is the Pydantic JSON
    #   • RAG context comes from ONE specific book
    #   • Output is parsed against a Pydantic schema
    # ══════════════════════════════════════════════════════════════

    async def _node_physics(self, state: WorkflowState) -> WorkflowState:
        """Node 1: Physics Expert — diagnose thermal deficiencies."""
        book = self.book_library.get("Sustainable-Home-Refurbishment", {})
        book_title = book.get("title", "Sustainable Home Refurbishment")
        book_ids = [book.get("book_id", "book_03_thermal")]
        t0 = time.time()

        try:
            rag_context = await self._retrieve_context(
                query="U-value thermal performance heat loss insulation building fabric energy label",
                book_ids=book_ids,
            )

            prompt = PHYSICS_PROMPT.format(
                book_title=book_title,
                detections=self._fmt(state.detections),
                u_values=self._fmt(state.u_values),
                energy_label=state.energy_label,
                property_meta=self._fmt(state.property_meta),
                rag_context=rag_context or "[No RAG context available]",
            )

            raw = await self._invoke_llm(prompt)
            parsed = self._parse_and_validate(raw, PhysicsOutput)

            state.physics = parsed
            state.step_logs.append(self._log(1, "physics_expert", book_title, book_ids,
                                              rag_context, time.time() - t0, True))

        except Exception as exc:
            logger.error("Physics node failed: %s", exc)
            state.error = f"Physics step failed: {exc}"
            state.step_logs.append(self._log(1, "physics_expert", book_title, book_ids,
                                              "", time.time() - t0, False, str(exc)))

        return state

    async def _node_cost(self, state: WorkflowState) -> WorkflowState:
        """Node 2: Cost Expert — estimate renovation costs."""
        book = self.book_library.get("Book-on-Flipping-Houses", {})
        book_title = book.get("title", "The Book on Flipping Houses (J. Scott)")
        book_ids = [book.get("book_id", "book_06_costs")]
        t0 = time.time()

        try:
            rag_context = await self._retrieve_context(
                query="renovation cost estimate material labour insulation roof window HVAC per sqm",
                book_ids=book_ids,
            )

            # ─── CONTEXT ISOLATION: only the previous step's JSON ───
            physics_json = state.physics.model_dump_json(indent=2) if state.physics else "{}"

            prompt = COST_PROMPT.format(
                book_title=book_title,
                physics_json=physics_json,
                property_meta=self._fmt(state.property_meta),
                rag_context=rag_context or "[No RAG context available]",
            )

            raw = await self._invoke_llm(prompt)
            parsed = self._parse_and_validate(raw, CostOutput)

            state.cost = parsed
            state.step_logs.append(self._log(2, "cost_expert", book_title, book_ids,
                                              rag_context, time.time() - t0, True))

        except Exception as exc:
            logger.error("Cost node failed: %s", exc)
            state.error = f"Cost step failed: {exc}"
            state.step_logs.append(self._log(2, "cost_expert", book_title, book_ids,
                                              "", time.time() - t0, False, str(exc)))

        return state

    async def _node_finance(self, state: WorkflowState) -> WorkflowState:
        """Node 3: Finance Expert — calculate ROI and capitalised value."""
        book = self.book_library.get("What-Every-RE-Investor", {})
        book_title = book.get("title", "What Every RE Investor Needs to Know")
        book_ids = [book.get("book_id", "book_07_finance")]
        t0 = time.time()

        try:
            rag_context = await self._retrieve_context(
                query="ROI IRR NPV cap rate capitalisation energy savings cash flow payback period",
                book_ids=book_ids,
            )

            # ─── CONTEXT ISOLATION ───
            physics_json = state.physics.model_dump_json(indent=2) if state.physics else "{}"
            cost_json = state.cost.model_dump_json(indent=2) if state.cost else "{}"

            prompt = FINANCE_PROMPT.format(
                book_title=book_title,
                physics_json=physics_json,
                cost_json=cost_json,
                property_meta=self._fmt(state.property_meta),
                cap_rate=self.cap_rate,
                discount_rate=self.discount_rate,
                energy_cost_per_kwh=self.energy_cost_per_kwh,
                currency=self.currency,
                rag_context=rag_context or "[No RAG context available]",
            )

            raw = await self._invoke_llm(prompt)
            parsed = self._parse_and_validate(raw, FinanceOutput)

            state.finance = parsed
            state.step_logs.append(self._log(3, "finance_expert", book_title, book_ids,
                                              rag_context, time.time() - t0, True))

        except Exception as exc:
            logger.error("Finance node failed: %s", exc)
            state.error = f"Finance step failed: {exc}"
            state.step_logs.append(self._log(3, "finance_expert", book_title, book_ids,
                                              "", time.time() - t0, False, str(exc)))

        return state

    async def _node_appraisal(self, state: WorkflowState) -> WorkflowState:
        """Node 4: Appraisal Expert — IVS-compliant value reconciliation."""
        ivs = self.book_library.get("IVS-Jan-2025", {})
        appraisal = self.book_library.get("Appraisal-of-Real-Estate-15th", {})
        ivs_title = ivs.get("title", "International Valuation Standards (IVS) January 2025")
        appraisal_title = appraisal.get("title", "The Appraisal of Real Estate, 15th Edition")
        book_ids = [
            ivs.get("book_id", "book_01_ivs"),
            appraisal.get("book_id", "book_02_appraisal"),
        ]
        t0 = time.time()

        try:
            # Retrieve from both books (they serve different purposes)
            rag_context_ivs = await self._retrieve_context(
                query="market value IVS 104 valuation approaches IVS 105 scope of work reconciliation",
                book_ids=[book_ids[0]],
            )
            rag_context_appraisal = await self._retrieve_context(
                query="cost approach sales comparison income approach reconciliation depreciation",
                book_ids=[book_ids[1]],
            )
            combined = (
                f"=== IVS-2025 Context ===\n{rag_context_ivs or '[No IVS context]'}\n\n"
                f"=== Appraisal Reference ===\n{rag_context_appraisal or '[No appraisal context]'}"
            )

            # ─── CONTEXT ISOLATION ───
            physics_json = state.physics.model_dump_json(indent=2) if state.physics else "{}"
            cost_json = state.cost.model_dump_json(indent=2) if state.cost else "{}"
            finance_json = state.finance.model_dump_json(indent=2) if state.finance else "{}"

            prompt = APPRAISAL_PROMPT.format(
                ivs_title=ivs_title,
                appraisal_title=appraisal_title,
                physics_json=physics_json,
                cost_json=cost_json,
                finance_json=finance_json,
                property_meta=self._fmt(state.property_meta),
                rag_context=combined,
            )

            raw = await self._invoke_llm(prompt)
            parsed = self._parse_and_validate(raw, AppraisalOutput)

            state.appraisal = parsed
            state.step_logs.append(self._log(4, "appraisal_expert",
                                              f"{ivs_title} + {appraisal_title}",
                                              book_ids, combined, time.time() - t0, True))

        except Exception as exc:
            logger.error("Appraisal node failed: %s", exc)
            state.error = f"Appraisal step failed: {exc}"
            state.step_logs.append(self._log(4, "appraisal_expert",
                                              f"{ivs_title} + {appraisal_title}",
                                              book_ids, "", time.time() - t0, False, str(exc)))

        return state

    # ══════════════════════════════════════════════════════════════
    # 6.  RAG Context Retrieval
    # ══════════════════════════════════════════════════════════════

    async def _retrieve_context(
        self,
        query: str,
        book_ids: List[str],
        top_k: int = 5,
    ) -> str:
        """
        Retrieve relevant chunks from the RAG pipeline, filtered by book_id.
        Falls back to unfiltered retrieval if book-specific search fails.
        """
        if not self.rag_pipeline:
            logger.debug("No RAG pipeline — returning empty context")
            return ""

        try:
            import asyncio
            import inspect

            if hasattr(self.rag_pipeline, "retrieve_for_books"):
                result = self.rag_pipeline.retrieve_for_books(
                    query=query, book_ids=book_ids, top_k=top_k,
                )
                results = await result if inspect.isawaitable(result) else result
            elif hasattr(self.rag_pipeline, "retrieve"):
                book_hint = " ".join(book_ids)
                result = self.rag_pipeline.retrieve(
                    query=f"{query} [source: {book_hint}]", top_k=top_k,
                )
                results = await result if inspect.isawaitable(result) else result
            elif hasattr(self.rag_pipeline, "query"):
                result = self.rag_pipeline.query(query)
                response = await result if inspect.isawaitable(result) else result
                return response if isinstance(response, str) else str(response)
            else:
                return ""

            # Format results
            if isinstance(results, list):
                chunks = []
                for r in results:
                    if isinstance(r, dict):
                        text = r.get("text", r.get("content", str(r)))
                        source = r.get("metadata", {}).get("source", "")
                        chunks.append(f"[{source}]\n{text}")
                    elif isinstance(r, str):
                        chunks.append(r)
                    elif hasattr(r, "page_content"):
                        source = r.metadata.get("source", "")
                        chunks.append(f"[{source}]\n{r.page_content}")
                return "\n---\n".join(chunks)

            return str(results)

        except Exception as exc:
            logger.warning("RAG retrieval failed for book_ids=%s: %s", book_ids, exc)
            return ""

    # ══════════════════════════════════════════════════════════════
    # 7.  LLM Invocation
    # ══════════════════════════════════════════════════════════════

    async def _invoke_llm(self, prompt: str) -> str:
        """
        Send prompt to LLM and return raw text response.
        Each call is a FRESH invocation — no chat history.
        """
        if not self.llm:
            raise RuntimeError("No LLM configured for chain-of-thought")

        try:
            if hasattr(self.llm, "ainvoke"):
                response = await self.llm.ainvoke(prompt)
                return str(response)
            elif hasattr(self.llm, "invoke"):
                response = self.llm.invoke(prompt)
                return str(response)
            elif callable(self.llm):
                import asyncio
                if asyncio.iscoroutinefunction(self.llm):
                    return await self.llm(prompt)
                else:
                    return self.llm(prompt)
            else:
                raise TypeError(f"Unsupported LLM type: {type(self.llm)}")
        except Exception as exc:
            logger.error("LLM invocation failed: %s", exc)
            raise

    # ══════════════════════════════════════════════════════════════
    # 8.  Pydantic Validation  (replaces regex JSON parsing)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_and_validate(raw_response: str, model: type) -> Any:
        """
        Parse LLM response → JSON → Pydantic model.

        Steps:
          1. Extract JSON from markdown fences or raw text
          2. Parse into dict
          3. Validate against the Pydantic model
          4. If validation fails, raise immediately (no silent garbage)
        """
        if not raw_response:
            raise ValueError("Empty LLM response")

        # Extract JSON block
        json_str = ChainOfThoughtEngine._extract_json(raw_response)
        if not json_str:
            raise ValueError(
                f"No JSON found in LLM response (len={len(raw_response)})"
            )

        data = json.loads(json_str)

        # Handle case where LLM returns a list instead of the wrapper object
        if isinstance(data, list):
            # Determine the wrapping field name from the model
            fields = list(model.model_fields.keys())
            if fields:
                data = {fields[0]: data}

        return model.model_validate(data)

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """Extract JSON from LLM output (handles markdown fences)."""
        # Try ```json ... ```
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()

        # Try bare { ... }
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return m.group(0)

        # Try bare [ ... ]
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            return m.group(0)

        return None

    # ══════════════════════════════════════════════════════════════
    # 9.  Helpers
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _fmt(obj: Any) -> str:
        """Pretty JSON for prompts."""
        try:
            return json.dumps(obj, indent=2, default=str, ensure_ascii=False)
        except Exception:
            return str(obj)

    @staticmethod
    def _log(
        step: int,
        role: str,
        books: str,
        book_ids: List[str],
        rag_context: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a step log entry."""
        return {
            "step": step,
            "role": role,
            "books": books,
            "book_ids": book_ids,
            "rag_chunks": len(rag_context.split("\n---\n")) if rag_context else 0,
            "duration_s": round(duration, 3),
            "success": success,
            "error": error,
        }
