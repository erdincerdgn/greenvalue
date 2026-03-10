"""
GreenValue AI — Report Engine

Central orchestrator that coordinates:
  1. Chain-of-thought multi-book reasoning  (LangGraph v2 — isolated agents)
  2. IVS-compliant section population
  3. Chart generation
  4. PDF rendering  (WeasyPrint: HTML/CSS → PDF)

Usage:
    engine = ReportEngine(rag_pipeline, chain_engine)
    result = await engine.generate(property_id, analysis, config)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .ivs_template import (
    ComparableProperty,
    EnergyAssessment,
    IVSReportData,
    IVSSection,
    IVSTemplate,
    MarketAnalysis,
    PropertyDescription,
    Reconciliation,
    RenovationImpact,
    UpgradeRecommendation,
    ValuationApproach,
)

logger = logging.getLogger("greenvalue-report")


# ──────────────────────────────────────────────
# Enums & Config
# ──────────────────────────────────────────────

class ReportType(str, Enum):
    """Available report variants."""
    FULL_IVS = "full_ivs"          # Complete IVS-2025 valuation report
    SUMMARY = "summary"            # Executive summary (cover + reconciliation + upgrades)
    ENERGY_ONLY = "energy_only"    # Energy assessment + renovation impact only
    UPGRADE_CARD = "upgrade_card"  # Single-page upgrade impact card (mobile)


@dataclass
class ReportConfig:
    """Configuration for a single report generation run."""
    report_type: ReportType = ReportType.FULL_IVS
    language: str = "en"                       # "en", "tr", "de"
    include_heatmap: bool = True
    include_charts: bool = True
    include_appendices: bool = True
    branding: Dict[str, str] = field(default_factory=lambda: {
        "company_name": "GreenValue AI",
        "logo_path": "",
        "accent_color": "#2E7D32",             # Green
        "footer_text": "Powered by GreenValue AI — IVS 2025 Compliant",
    })
    max_comparable_properties: int = 5
    currency_symbol: str = "€"
    currency_code: str = "EUR"
    # Sections to include (None = all for report_type)
    sections_override: Optional[List[IVSSection]] = None


@dataclass
class ReportResult:
    """Output of a report generation run."""
    report_id: str = ""
    property_id: str = ""
    report_type: ReportType = ReportType.FULL_IVS
    pdf_bytes: bytes = b""
    metadata: Dict[str, Any] = field(default_factory=dict)
    ivs_compliance_warnings: List[str] = field(default_factory=list)
    chain_of_thought_log: List[Dict] = field(default_factory=list)
    sections_generated: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    generation_time_seconds: float = 0.0


# ──────────────────────────────────────────────
# Report Engine
# ──────────────────────────────────────────────

class ReportEngine:
    """
    IVS-2025-compliant report orchestrator.

    Flows:
      1. Gather analysis data (YOLO detections, U-value physics, heatmap)
      2. Run chain-of-thought through multi-book RAG
      3. Populate IVSReportData sections
      4. Generate charts / visualisations
      5. Render PDF via pdf_renderer
      6. Validate IVS compliance
      7. Return ReportResult
    """

    def __init__(
        self,
        rag_pipeline: Optional[Any] = None,
        chain_engine: Optional[Any] = None,
        section_generators: Optional[Dict] = None,
        chart_renderer: Optional[Any] = None,
        pdf_renderer: Optional[Any] = None,
    ):
        self.rag_pipeline = rag_pipeline
        self.chain_engine = chain_engine
        self._section_generators = section_generators or {}
        self._chart_renderer = chart_renderer
        self._pdf_renderer = pdf_renderer
        logger.info("ReportEngine initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        property_id: str,
        analysis_result: Dict[str, Any],
        config: Optional[ReportConfig] = None,
    ) -> ReportResult:
        """
        Generate a complete IVS-2025-compliant report.

        Parameters
        ----------
        property_id : str
            Unique property identifier.
        analysis_result : dict
            Combined output from Vision + Physics + RAG pipelines.
            Expected keys: detections, u_values, heatmap_path,
            energy_label, property_meta, …
        config : ReportConfig, optional
            Report configuration. Defaults to full IVS.

        Returns
        -------
        ReportResult
        """
        import time
        start = time.time()

        config = config or ReportConfig()
        report_id = f"GV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        logger.info("Generating %s report %s for property %s",
                     config.report_type.value, report_id, property_id)

        result = ReportResult(
            report_id=report_id,
            property_id=property_id,
            report_type=config.report_type,
        )

        try:
            # 1. Build base IVS data structure
            report_data = IVSTemplate.build_empty_report(
                property_id=property_id,
                address=analysis_result.get("address", ""),
                report_number=report_id,
            )

            # 2. Populate property description from analysis
            self._populate_property(report_data, analysis_result)

            # 2b. Populate market analysis
            self._populate_market(report_data, analysis_result)

            # 3. Populate energy assessment from physics pipeline
            self._populate_energy(report_data, analysis_result)

            # 4. Run chain-of-thought for renovation impact
            chain_log = await self._run_chain_of_thought(
                report_data, analysis_result, config
            )
            result.chain_of_thought_log = chain_log

            # 5. Populate valuation approaches
            self._populate_valuation(report_data, analysis_result)

            # 6. Reconcile final value
            self._reconcile(report_data, analysis_result)

            # 7. Generate charts
            chart_paths = {}
            if config.include_charts and self._chart_renderer:
                chart_paths = await self._generate_charts(report_data, config)

            # 8. Render PDF
            sections = self._get_sections_for_type(config)
            result.sections_generated = [s.value for s in sections]

            if self._pdf_renderer:
                result.pdf_bytes = await self._pdf_renderer.render(
                    report_data=report_data,
                    sections=sections,
                    config=config,
                    chart_paths=chart_paths,
                )
            else:
                # Fallback: return data as JSON metadata
                result.metadata["report_data_summary"] = self._summarise_data(report_data)
                logger.warning("No PDF renderer configured — returning metadata only")

            # 9. Validate IVS compliance
            result.ivs_compliance_warnings = report_data.validate_ivs_compliance()
            if result.ivs_compliance_warnings:
                logger.warning(
                    "IVS compliance warnings for %s: %s",
                    report_id, result.ivs_compliance_warnings
                )

            result.metadata["charts"] = chart_paths
            result.metadata["language"] = config.language
            result.metadata["currency"] = config.currency_code

        except Exception as exc:
            logger.error("Report generation failed for %s: %s", report_id, exc, exc_info=True)
            result.metadata["error"] = str(exc)

        result.generation_time_seconds = round(time.time() - start, 3)
        logger.info(
            "Report %s generated in %.2fs (%d warnings)",
            report_id, result.generation_time_seconds,
            len(result.ivs_compliance_warnings)
        )
        return result

    async def generate_json(
        self,
        property_id: str,
        analysis_result: Dict[str, Any],
        config: Optional[ReportConfig] = None,
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON report (no PDF rendering).

        Returns a dict with all IVS sections, chain-of-thought log,
        compliance warnings, and report metadata — suitable for
        API responses or frontend rendering.
        """
        import time as _time
        start = _time.time()
        config = config or ReportConfig()
        report_id = f"GV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        logger.info("Generating JSON report %s for property %s", report_id, property_id)

        try:
            # Build base IVS data structure
            report_data = IVSTemplate.build_empty_report(
                property_id=property_id,
                address=analysis_result.get("address", ""),
                report_number=report_id,
            )

            # Populate all sections (same as PDF flow)
            self._populate_property(report_data, analysis_result)
            self._populate_market(report_data, analysis_result)
            self._populate_energy(report_data, analysis_result)

            chain_log = await self._run_chain_of_thought(report_data, analysis_result, config)
            self._populate_valuation(report_data, analysis_result)
            self._reconcile(report_data, analysis_result)

            # Get sections for this report type
            sections = self._get_sections_for_type(config)

            # Build section data via SectionGenerator
            from .sections import SectionGenerator
            sec_gen = SectionGenerator(report_data, config.language, config.currency_code)

            section_data = {}
            for section in sections:
                method_name = f"_{section.value}"
                if hasattr(sec_gen, method_name):
                    section_data[section.value] = getattr(sec_gen, method_name)()

            # Validate IVS compliance
            ivs_warnings = report_data.validate_ivs_compliance()

            generation_time = round(_time.time() - start, 3)

            return {
                "report_id": report_id,
                "property_id": property_id,
                "report_type": config.report_type.value,
                "language": config.language,
                "currency": config.currency_code,
                "generated_at": datetime.utcnow().isoformat(),
                "generation_time_seconds": generation_time,
                "sections": section_data,
                "sections_generated": [s.value for s in sections],
                "ivs_compliance_warnings": ivs_warnings,
                "chain_of_thought_log": chain_log,
                "summary": self._summarise_data(report_data),
            }

        except Exception as exc:
            logger.error("JSON report generation failed: %s", exc, exc_info=True)
            return {
                "report_id": report_id,
                "property_id": property_id,
                "error": str(exc),
                "generated_at": datetime.utcnow().isoformat(),
            }

    # ------------------------------------------------------------------
    # Internal: section population
    # ------------------------------------------------------------------

    def _populate_property(
        self, report: IVSReportData, analysis: Dict[str, Any]
    ) -> None:
        """Fill Property Description from analysis detections."""
        meta = analysis.get("property_meta", {})
        report.property_desc.property_type = meta.get("type", "Residential")
        report.property_desc.building_year = meta.get("year_built")
        report.property_desc.area_sqm = meta.get("area_sqm")
        report.property_desc.num_floors = meta.get("floors")
        report.property_desc.zoning = meta.get("zoning", "")

        # Map YOLO detections to property components
        detections = analysis.get("detections", [])
        for det in detections:
            report.property_desc.detected_components.append({
                "type": det.get("class_name", "unknown"),
                "condition": det.get("condition", "fair"),
                "u_value": det.get("u_value"),
                "area": det.get("area_sqm"),
                "confidence": det.get("confidence", 0.0),
            })

    def _populate_market(
        self, report: IVSReportData, analysis: Dict[str, Any]
    ) -> None:
        """Fill Market Analysis from comparable data and market indicators."""
        mkt = analysis.get("market", {})
        if not mkt:
            return

        report.market.market_area = mkt.get("market_area", analysis.get("address", ""))
        report.market.median_price_sqm = mkt.get("median_price_sqm", 0.0)
        report.market.price_trend_pct = mkt.get("price_trend_pct", 0.0)
        report.market.avg_days_on_market = mkt.get("avg_days_on_market", 0)
        report.market.inventory_level = mkt.get("inventory_level", "")
        report.market.energy_premium_pct = mkt.get("energy_premium_pct", 0.0)
        report.market.market_narrative = mkt.get("narrative", "")
        report.market.data_source_notes = mkt.get("data_source_notes", [])

        # Comparable properties
        comps = mkt.get("comparable_properties", [])
        for c in comps:
            comp = ComparableProperty(
                address=c.get("address", ""),
                sale_date=c.get("sale_date", ""),
                sale_price=c.get("sale_price", 0.0),
                area_sqm=c.get("area_sqm", 0.0),
                price_per_sqm=c.get("price_per_sqm", 0.0),
                energy_label=c.get("energy_label", ""),
                similarity_score=c.get("similarity_score", 0.0),
                adjustments=c.get("adjustments", []),
                adjusted_price=c.get("adjusted_price", 0.0),
            )
            report.market.comparable_properties.append(comp)

    def _populate_energy(
        self, report: IVSReportData, analysis: Dict[str, Any]
    ) -> None:
        """Fill Energy Assessment from physics pipeline."""
        energy = analysis.get("energy", {})
        report.energy.energy_label_current = energy.get("label_current", "")
        report.energy.energy_label_projected = energy.get("label_projected", "")
        report.energy.total_heat_loss_kwh = energy.get("heat_loss_kwh", 0.0)
        report.energy.carbon_footprint_kg = energy.get("carbon_kg", 0.0)
        report.energy.heatmap_path = analysis.get("heatmap_path")

        u_values = analysis.get("u_values", [])
        for uv in u_values:
            report.energy.component_u_values.append({
                "component": uv.get("component", ""),
                "u_value_current": uv.get("u_value", 0.0),
                "u_value_target": uv.get("u_value_target", 0.0),
                "condition": uv.get("condition", ""),
                "area_sqm": uv.get("area_sqm", 0.0),
            })

    async def _run_chain_of_thought(
        self,
        report: IVSReportData,
        analysis: Dict[str, Any],
        config: ReportConfig,
    ) -> List[Dict]:
        """
        Execute multi-book chain-of-thought reasoning:
          Physics → Cost → Finance → Appraisal

        Populates report.renovation with upgrade recommendations.
        """
        chain_log: List[Dict] = []

        if not self.chain_engine:
            logger.info("No ChainOfThoughtEngine — skipping multi-book chain")
            return chain_log

        try:
            import asyncio
            chain_result = await asyncio.wait_for(
                self.chain_engine.execute(
                    detections=analysis.get("detections", []),
                    u_values=analysis.get("u_values", []),
                    energy_label=analysis.get("energy", {}).get("label_current", ""),
                    property_meta=analysis.get("property_meta", {}),
                ),
                timeout=120,
            )

            # Map chain result to report renovation section
            for upgrade in chain_result.upgrades:
                rec = UpgradeRecommendation(
                    component=upgrade.get("component", ""),
                    description=upgrade.get("description", ""),
                    estimated_cost=upgrade.get("cost", 0.0),
                    estimated_value_add=upgrade.get("value_add", 0.0),
                    roi_percent=upgrade.get("roi_percent", 0.0),
                    payback_years=upgrade.get("payback_years", 0.0),
                    energy_savings_kwh=upgrade.get("energy_savings_kwh", 0.0),
                    co2_reduction_kg=upgrade.get("co2_reduction_kg", 0.0),
                    energy_label_impact=upgrade.get("label_impact", ""),
                    cost_source=upgrade.get("cost_source", ""),
                    finance_source=upgrade.get("finance_source", ""),
                    valuation_method=upgrade.get("valuation_method", ""),
                )
                report.renovation.upgrades.append(rec)

            # Aggregate renovation totals
            report.renovation.total_cost = sum(u.estimated_cost for u in report.renovation.upgrades)
            report.renovation.total_value_add = sum(u.estimated_value_add for u in report.renovation.upgrades)
            if report.renovation.total_cost > 0:
                report.renovation.aggregate_roi = (
                    (report.renovation.total_value_add - report.renovation.total_cost)
                    / report.renovation.total_cost * 100
                )
            report.renovation.before_label = analysis.get("energy", {}).get("label_current", "")
            report.renovation.after_label = analysis.get("energy", {}).get("label_projected", "")

            chain_log = chain_result.step_logs

        except Exception as exc:
            logger.error("Chain-of-thought failed: %s", exc, exc_info=True)
            chain_log.append({"error": str(exc)})

        return chain_log

    def _populate_valuation(
        self, report: IVSReportData, analysis: Dict[str, Any]
    ) -> None:
        """
        Fill valuation approaches from analysis + renovation data.
        Uses IVS 105 three-approach framework.
        """
        val_data = analysis.get("valuation", {})

        for approach in report.valuation_approaches:
            if approach.approach_name == "Cost Approach":
                approach.value_estimate = val_data.get("cost_approach_value")
                approach.methodology = (
                    "Replacement cost new less depreciation (physical, functional, external), "
                    "plus site value. Renovation impact added per chain-of-thought analysis."
                )
                approach.weight_in_reconciliation = val_data.get("cost_weight", 0.25)
                approach.data_sources = [
                    "The Appraisal of Real Estate, 15th Ed. — Ch. 17",
                    "Sustainable Construction — material cost benchmarks",
                    "The Book on Flipping Houses — renovation cost data",
                ]
                # Add renovation value add
                if report.renovation.total_value_add > 0 and approach.value_estimate:
                    approach.adjustments.append({
                        "type": "green_upgrade_value",
                        "amount": report.renovation.total_value_add,
                        "source": "Chain-of-thought: Physics→Cost→Finance→Appraisal",
                    })

            elif approach.approach_name == "Sales Comparison Approach":
                approach.value_estimate = val_data.get("sales_comparison_value")
                approach.methodology = (
                    "Analysis of comparable sales with adjustments for location, size, "
                    "condition, and energy performance. Green premium adjustment applied "
                    "based on energy label differential."
                )
                approach.weight_in_reconciliation = val_data.get("comparison_weight", 0.50)
                approach.data_sources = [
                    "The Appraisal of Real Estate, 15th Ed. — Ch. 14-15",
                    "IVS-Jan-2025 — Market Value definition (IVS 104)",
                ]

            elif approach.approach_name == "Income Approach":
                approach.value_estimate = val_data.get("income_approach_value")
                approach.methodology = (
                    "Direct capitalisation of net operating income with "
                    "capitalisation rate derived from market comparables. "
                    "Energy savings capitalised as additional income stream."
                )
                approach.weight_in_reconciliation = val_data.get("income_weight", 0.25)
                approach.data_sources = [
                    "The Appraisal of Real Estate, 15th Ed. — Ch. 20-21",
                    "What Every RE Investor Needs to Know — Cap Rate, NOI, GRM",
                ]

    def _reconcile(
        self, report: IVSReportData, analysis: Dict[str, Any]
    ) -> None:
        """
        Reconcile the three approaches into a final value opinion (IVS 105).
        """
        values = []
        for approach in report.valuation_approaches:
            if approach.applicable and approach.value_estimate:
                values.append(
                    (approach.approach_name, approach.value_estimate, approach.weight_in_reconciliation)
                )

        if not values:
            report.reconciliation.reconciliation_narrative = (
                "Insufficient data for valuation reconciliation. "
                "Report limited to energy assessment and renovation impact analysis."
            )
            report.reconciliation.confidence_level = "Low"
            return

        # Weighted average
        weighted_sum = sum(v * w for _, v, w in values)
        weight_total = sum(w for _, _, w in values)
        reconciled = weighted_sum / weight_total if weight_total > 0 else 0

        report.reconciliation.reconciled_value = round(reconciled, 2)

        # Green premium
        green_premium = analysis.get("valuation", {}).get("green_premium", 0.0)
        report.reconciliation.green_premium_amount = green_premium
        report.reconciliation.green_premium_basis = (
            "IVS-Jan-2025 guidance on sustainability and ESG in valuation; "
            "energy label differential analysis per Sustainable Home Refurbishment methodology"
        )

        # Set individual approach values for reconciliation display
        for approach_name, value, _ in values:
            if "Cost" in approach_name:
                report.reconciliation.cost_approach_value = value
            elif "Sales" in approach_name or "Comparison" in approach_name:
                report.reconciliation.sales_comparison_value = value
            elif "Income" in approach_name:
                report.reconciliation.income_approach_value = value

        # Narrative
        approach_lines = [
            f"  - {name}: {analysis.get('valuation', {}).get('currency', '€')}{value:,.0f} (weight: {w:.0%})"
            for name, value, w in values
        ]
        report.reconciliation.reconciliation_narrative = (
            f"The reconciled Market Value (IVS 104) is derived from "
            f"{len(values)} applicable approach(es):\n"
            + "\n".join(approach_lines)
            + f"\n\nReconciled Value: {analysis.get('valuation', {}).get('currency', '€')}"
            f"{reconciled:,.0f}"
        )

        # Confidence level based on data quality
        if len(values) >= 3 and all(w > 0 for _, _, w in values):
            report.reconciliation.confidence_level = "High"
        elif len(values) >= 2:
            report.reconciliation.confidence_level = "Moderate"
        else:
            report.reconciliation.confidence_level = "Low"

    # ------------------------------------------------------------------
    # Chart generation
    # ------------------------------------------------------------------

    async def _generate_charts(
        self, report: IVSReportData, config: ReportConfig
    ) -> Dict[str, str]:
        """Generate all charts and return {chart_name: file_path}."""
        paths = {}
        if not self._chart_renderer:
            return paths

        try:
            # 1. Energy label gauge (A–G thermometer with current/projected arrows)
            paths["energy_gauge"] = await self._chart_renderer.energy_gauge(
                current_label=report.energy.energy_label_current,
                projected_label=report.energy.energy_label_projected,
            )

            # 2. Before/After energy comparison bars
            total_savings_kwh = sum(
                u.energy_savings_kwh for u in report.renovation.upgrades
            )
            total_co2_reduction = sum(
                u.co2_reduction_kg for u in report.renovation.upgrades
            )
            paths["before_after"] = await self._chart_renderer.before_after_comparison(
                current_label=report.energy.energy_label_current,
                projected_label=report.energy.energy_label_projected,
                current_heat_loss=report.energy.total_heat_loss_kwh,
                projected_heat_loss=max(
                    0, report.energy.total_heat_loss_kwh - total_savings_kwh
                ),
                current_carbon=report.energy.carbon_footprint_kg,
                projected_carbon=max(
                    0, report.energy.carbon_footprint_kg - total_co2_reduction
                ),
            )

            # 3. U-value comparison (current vs target per component)
            if report.energy.component_u_values:
                paths["u_value_comparison"] = await self._chart_renderer.u_value_comparison(
                    components=report.energy.component_u_values,
                )

            # 4. Heatmap overlay (composites thermal heatmap on property photo)
            if config.include_heatmap:
                paths["heatmap_overlay"] = await self._chart_renderer.heatmap_overlay(
                    property_photo_path=report.cover.property_photo_path,
                    heatmap_path=report.energy.heatmap_path,
                )

            # 5. ROI waterfall
            if report.renovation.upgrades:
                paths["roi_waterfall"] = await self._chart_renderer.roi_waterfall(
                    upgrades=report.renovation.upgrades,
                    currency=config.currency_symbol,
                )

            # 6. Cost breakdown pie chart
            if report.renovation.upgrades:
                paths["cost_breakdown"] = await self._chart_renderer.cost_breakdown_pie(
                    upgrades=report.renovation.upgrades,
                    currency=config.currency_symbol,
                )

            # 7. Cap Rate sensitivity (Income Approach transparency)
            income_approach = next(
                (a for a in report.valuation_approaches
                 if "Income" in a.approach_name and a.applicable and a.value_estimate),
                None,
            )
            if income_approach and income_approach.value_estimate:
                # Infer NOI from value × assumed cap rate (default 6%)
                cap_rate = 0.06
                noi = income_approach.value_estimate * cap_rate
                paths["cap_rate_sensitivity"] = await self._chart_renderer.cap_rate_sensitivity(
                    base_noi=noi,
                    base_cap_rate=cap_rate,
                    currency=config.currency_symbol,
                )

        except Exception as exc:
            logger.warning("Chart generation error: %s", exc)

        # Filter out empty paths
        paths = {k: v for k, v in paths.items() if v}
        return paths

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_sections_for_type(self, config: ReportConfig) -> List[IVSSection]:
        """Determine which sections to include based on report type."""
        if config.sections_override:
            return config.sections_override

        if config.report_type == ReportType.FULL_IVS:
            sections = list(IVSTemplate.SECTION_ORDER)
            if not config.include_appendices:
                sections = [
                    s for s in sections
                    if not s.value.startswith("appendix_")
                ]
            return sections

        elif config.report_type == ReportType.SUMMARY:
            return [
                IVSSection.COVER,
                IVSSection.SCOPE_OF_WORK,
                IVSSection.ENERGY_ASSESSMENT,
                IVSSection.RENOVATION_IMPACT,
                IVSSection.RECONCILIATION,
            ]

        elif config.report_type == ReportType.ENERGY_ONLY:
            return [
                IVSSection.COVER,
                IVSSection.PROPERTY_DESCRIPTION,
                IVSSection.ENERGY_ASSESSMENT,
                IVSSection.RENOVATION_IMPACT,
            ]

        elif config.report_type == ReportType.UPGRADE_CARD:
            return [
                IVSSection.ENERGY_ASSESSMENT,
                IVSSection.RENOVATION_IMPACT,
            ]

        return list(IVSTemplate.SECTION_ORDER)

    @staticmethod
    def _summarise_data(report: IVSReportData) -> Dict[str, Any]:
        """Create a JSON-serialisable summary when no PDF renderer is available."""
        return {
            "property_id": report.property_desc.property_id,
            "address": report.property_desc.address,
            "energy_label": report.energy.energy_label_current,
            "energy_label_projected": report.energy.energy_label_projected,
            "upgrade_count": len(report.renovation.upgrades),
            "total_renovation_cost": report.renovation.total_cost,
            "total_value_add": report.renovation.total_value_add,
            "aggregate_roi": report.renovation.aggregate_roi,
            "reconciled_value": report.reconciliation.reconciled_value,
            "confidence": report.reconciliation.confidence_level,
            "ivs_warnings": report.validate_ivs_compliance(),
        }
