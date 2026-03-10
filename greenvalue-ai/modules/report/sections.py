"""
GreenValue AI — IVS Report Section Generators

Each function generates content for one IVS-2025 section.
Called by ReportEngine during PDF rendering.

Outputs Markdown-formatted text blocks that the PDF renderer
converts to styled report pages.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import date

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
from .translations import t, t_glossary

logger = logging.getLogger("greenvalue-report")


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

def _fmt_currency(value: float, symbol: str = "€") -> str:
    """Format a number as currency."""
    if value >= 1_000_000:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.2f}"


def _label_color(label: str) -> str:
    """Return CSS color for an energy label."""
    colors = {
        "A": "#00B050", "B": "#92D050", "C": "#FFFF00",
        "D": "#FFC000", "E": "#FF6600", "F": "#FF0000", "G": "#C00000",
    }
    return colors.get(label.upper(), "#999999") if label else "#999999"


# ──────────────────────────────────────────────
# Section Generators
# ──────────────────────────────────────────────

class SectionGenerator:
    """Generates formatted content blocks for each IVS report section."""

    def __init__(self, report_data: IVSReportData, language: str = "en", currency: str = "€"):
        self.data = report_data
        self.lang = language
        self.currency = currency

    def generate(self, section: IVSSection) -> Dict[str, Any]:
        """
        Generate content for a given section.

        Returns dict with:
            title: str
            content: str  (markdown)
            tables: list[dict]  (for PDF table rendering)
            metadata: dict
        """
        generators = {
            IVSSection.COVER: self._cover,
            IVSSection.SCOPE_OF_WORK: self._scope_of_work,
            IVSSection.PROPERTY_DESCRIPTION: self._property_description,
            IVSSection.MARKET_ANALYSIS: self._market_analysis,
            IVSSection.VALUATION_APPROACHES: self._valuation_approaches,
            IVSSection.ENERGY_ASSESSMENT: self._energy_assessment,
            IVSSection.RENOVATION_IMPACT: self._renovation_impact,
            IVSSection.RECONCILIATION: self._reconciliation,
            IVSSection.ASSUMPTIONS: self._assumptions,
            IVSSection.APPENDIX_DETECTIONS: self._appendix_detections,
            IVSSection.APPENDIX_FINANCIALS: self._appendix_financials,
            IVSSection.APPENDIX_GLOSSARY: self._appendix_glossary,
            IVSSection.APPENDIX_SOURCES: self._appendix_sources,
        }

        gen_fn = generators.get(section)
        if not gen_fn:
            return {
                "title": section.value,
                "content": f"[Section {section.value} not implemented]",
                "tables": [],
                "metadata": {},
            }

        title = IVSTemplate.get_section_title(section, self.lang)
        content = gen_fn()

        return {
            "title": title,
            "content": content.get("text", ""),
            "tables": content.get("tables", []),
            "metadata": content.get("metadata", {}),
        }

    # ── Cover ──

    def _cover(self) -> Dict:
        c = self.data.cover
        L = self.lang
        text = (
            f"**{c.property_address}**\n\n"
            f"{t('report_number', L)}: {c.report_number}\n"
            f"{t('report_date', L)}: {c.report_date}\n"
            f"{t('valuation_date', L)}: {c.valuation_date}\n"
            f"{t('prepared_by', L)}: {c.appraiser_name}\n"
            f"{t('client', L)}: {c.client_name or t('na', L)}\n"
            f"{t('intended_use', L)}: {c.intended_use}\n"
        )
        return {"text": text, "metadata": {"photo_path": c.property_photo_path, "heatmap_path": c.heatmap_path}}

    # ── 1. Scope of Work (IVS 101) ──

    def _scope_of_work(self) -> Dict:
        s = self.data.scope
        L = self.lang
        assumptions_text = "\n".join(f"- {a}" for a in s.assumptions)
        special_text = "\n".join(f"- {a}" for a in s.special_assumptions) if s.special_assumptions else t("none", L)
        departures_text = "\n".join(f"- {d}" for d in s.departures_from_ivs) if s.departures_from_ivs else t("none", L)

        text = (
            f"**{t('purpose_of_valuation', L)}:** {s.purpose}\n\n"
            f"**{t('intended_use', L)}:** {s.intended_use}\n\n"
            f"**{t('type_of_value', L)}:** {s.type_of_value}\n\n"
            f"**{t('valuation_date', L)}:** {s.valuation_date}\n\n"
            f"**{t('inspection_date', L)}:** {s.inspection_date}\n\n"
            f"**{t('inspection_type', L)}:** {s.inspection_type}\n\n"
            f"### {t('assumptions_ivs', L)}\n{assumptions_text}\n\n"
            f"### {t('special_assumptions', L)}\n{special_text}\n\n"
            f"### {t('departures_from_ivs', L)}\n{departures_text}\n"
        )
        return {"text": text}

    # ── 2. Property Description ──

    def _property_description(self) -> Dict:
        p = self.data.property_desc
        L = self.lang
        text = (
            f"**{t('property_id', L)}:** {p.property_id}\n\n"
            f"**{t('address', L)}:** {p.address}\n\n"
            f"**{t('property_type', L)}:** {p.property_type}\n\n"
            f"**{t('year_built', L)}:** {p.building_year or t('unknown', L)}\n\n"
            f"**{t('gross_floor_area', L)}:** {p.area_sqm or t('unknown', L)} m²\n\n"
            f"**{t('number_of_floors', L)}:** {p.num_floors or t('unknown', L)}\n\n"
            f"**{t('zoning', L)}:** {p.zoning or t('na', L)}\n\n"
        )

        # Component table from YOLO detections
        if p.detected_components:
            text += f"### {t('detected_components', L)}\n\n"
            table = {
                "headers": [t('component', L), t('condition', L), t('u_value_header', L), t('area_header', L), t('ai_confidence', L)],
                "rows": [],
            }
            for comp in p.detected_components:
                table["rows"].append([
                    comp.get("type", "—"),
                    comp.get("condition", "—"),
                    f"{comp['u_value']:.2f}" if comp.get("u_value") else "—",
                    f"{comp['area']:.1f}" if comp.get("area") else "—",
                    f"{comp['confidence']:.0%}" if comp.get("confidence") else "—",
                ])
            return {"text": text, "tables": [table]}

        return {"text": text}

    # ── 3. Market Analysis ──

    def _market_analysis(self) -> Dict:
        m = self.data.market
        L = self.lang
        tables: List[Dict] = []

        # ── Market Overview ──
        text = f"### {t('market_overview', L)}\n\n"

        if m.market_area:
            text += f"**{t('market_area', L)}:** {m.market_area}\n\n"

        text += f"**{t('analysis_date', L)}:** {m.analysis_date}\n\n"

        if m.median_price_sqm:
            text += f"**{t('median_price_sqm', L)}:** {_fmt_currency(m.median_price_sqm, self.currency)}\n\n"

        if m.price_trend_pct:
            arrow = "↑" if m.price_trend_pct > 0 else ("↓" if m.price_trend_pct < 0 else "→")
            text += f"**{t('yoy_price_change', L)}:** {arrow} {m.price_trend_pct:+.1f}%\n\n"

        if m.avg_days_on_market:
            text += f"**{t('days_on_market', L)}:** {m.avg_days_on_market}\n\n"

        if m.inventory_level:
            text += f"**{t('inventory_level', L)}:** {m.inventory_level}\n\n"

        if m.energy_premium_pct:
            text += f"**{t('energy_premium', L)}:** +{m.energy_premium_pct:.1f}%\n\n"

        # ── Market narrative ──
        if m.market_narrative:
            text += f"{m.market_narrative}\n\n"
        else:
            text += (
                f"{t('market_analysis_note', L)}\n\n"
                f"- {t('market_factor_location', L)}\n"
                f"- {t('market_factor_supply', L)}\n"
                f"- {t('market_factor_energy', L)}\n"
                f"- {t('market_factor_comparable', L)}\n\n"
            )

        # ── Comparable Properties Table ──
        if m.comparable_properties:
            text += f"### {t('comparable_properties', L)}\n\n"
            comp_table = {
                "headers": [
                    t('comp_address', L),
                    t('comp_sale_date', L),
                    t('comp_sale_price', L),
                    t('comp_area_sqm', L),
                    t('comp_price_sqm', L),
                    t('comp_energy_label', L),
                    t('comp_adj_price', L),
                    t('comp_similarity', L),
                ],
                "rows": [],
            }
            for cp in m.comparable_properties:
                comp_table["rows"].append([
                    cp.address or "—",
                    cp.sale_date or "—",
                    _fmt_currency(cp.sale_price, self.currency) if cp.sale_price else "—",
                    f"{cp.area_sqm:.0f}" if cp.area_sqm else "—",
                    _fmt_currency(cp.price_per_sqm, self.currency) if cp.price_per_sqm else "—",
                    cp.energy_label or "—",
                    _fmt_currency(cp.adjusted_price, self.currency) if cp.adjusted_price else "—",
                    f"{cp.similarity_score:.0%}" if cp.similarity_score else "—",
                ])
            tables.append(comp_table)

        # ── Data Source Notes ──
        if m.data_source_notes:
            text += f"\n### {t('data_source_notes_heading', L)}\n\n"
            for note in m.data_source_notes:
                text += f"- {note}\n"
            text += "\n"

        text += f"{t('market_note_disclaimer', L)}\n"

        return {"text": text, "tables": tables}

    # ── 4. Valuation Approaches (IVS 105) ──

    def _valuation_approaches(self) -> Dict:
        L = self.lang
        tables = []
        text = ""

        for approach in self.data.valuation_approaches:
            text += f"### {approach.approach_name}\n\n"
            text += f"**{t('applicable', L)}:** {t('yes', L) if approach.applicable else t('no', L)}\n\n"

            if approach.value_estimate:
                text += f"**{t('indicated_value', L)}:** {_fmt_currency(approach.value_estimate, self.currency)}\n\n"

            text += f"**{t('methodology', L)}:** {approach.methodology}\n\n"

            if approach.data_sources:
                text += f"**{t('data_sources', L)}:**\n"
                for src in approach.data_sources:
                    text += f"- {src}\n"
                text += "\n"

            if approach.adjustments:
                text += f"**{t('adjustments', L)}:**\n"
                adj_table = {
                    "headers": [t('adj_type', L), t('adj_amount', L), t('adj_source', L)],
                    "rows": [
                        [
                            adj.get("type", "—"),
                            _fmt_currency(adj.get("amount", 0), self.currency),
                            adj.get("source", "—"),
                        ]
                        for adj in approach.adjustments
                    ],
                }
                tables.append(adj_table)

            text += f"**{t('weight_in_reconciliation', L)}:** {approach.weight_in_reconciliation:.0%}\n\n"
            text += f"**{t('book_reference', L)}:** {approach.book_reference}\n\n---\n\n"

        return {"text": text, "tables": tables}

    # ── 5. Energy & Sustainability Assessment ──

    def _energy_assessment(self) -> Dict:
        e = self.data.energy
        L = self.lang
        text = (
            f"### {t('current_energy_performance', L)}\n\n"
            f"**{t('energy_label_current', L)}:** {e.energy_label_current or t('not_assessed', L)}\n\n"
            f"**{t('energy_label_projected', L)}:** {e.energy_label_projected or t('na', L)}\n\n"
            f"**{t('annual_heat_loss', L)}:** {e.total_heat_loss_kwh:,.0f} kWh/year\n\n"
            f"**{t('carbon_footprint', L)}:** {e.carbon_footprint_kg:,.0f} kg CO₂/year\n\n"
        )

        if e.component_u_values:
            text += f"### {t('component_thermal', L)}\n\n"
            table = {
                "headers": [t('component', L), t('current_u_value', L), t('target_u_value', L), t('condition', L), t('area_header', L)],
                "rows": [
                    [
                        uv.get("component", "—"),
                        f"{uv.get('u_value_current', 0):.2f}",
                        f"{uv.get('u_value_target', 0):.2f}",
                        uv.get("condition", "—"),
                        f"{uv.get('area_sqm', 0):.1f}",
                    ]
                    for uv in e.component_u_values
                ],
            }
            return {"text": text, "tables": [table], "metadata": {"heatmap_path": e.heatmap_path}}

        return {"text": text, "metadata": {"heatmap_path": e.heatmap_path}}

    # ── 6. Renovation Impact Analysis ──

    def _renovation_impact(self) -> Dict:
        r = self.data.renovation
        L = self.lang
        if not r.upgrades:
            return {"text": f"{t('no_upgrades', L)}\n"}

        text = (
            f"### {t('upgrade_summary', L)}\n\n"
            f"**{t('total_estimated_cost', L)}:** {_fmt_currency(r.total_cost, self.currency)}\n\n"
            f"**{t('total_value_add', L)}:** {_fmt_currency(r.total_value_add, self.currency)}\n\n"
            f"**{t('aggregate_roi', L)}:** {r.aggregate_roi:.1f}%\n\n"
            f"**{t('aggregate_payback', L)}:** {r.aggregate_payback_years:.1f} years\n\n"
            f"**{t('energy_label_impact', L)}:** {r.before_label} → {r.after_label}\n\n"
            f"### {t('individual_upgrades', L)}\n\n"
        )

        table = {
            "headers": [
                t('component', L), t('description', L), t('cost', L), t('value_add', L),
                t('roi', L), t('payback', L), t('energy_saving', L), t('label_impact', L)
            ],
            "rows": [],
        }
        for u in r.upgrades:
            table["rows"].append([
                u.component,
                u.description,
                _fmt_currency(u.estimated_cost, self.currency),
                _fmt_currency(u.estimated_value_add, self.currency),
                f"{u.roi_percent:.0f}%",
                f"{u.payback_years:.1f} yr",
                f"{u.energy_savings_kwh:,.0f} kWh",
                u.energy_label_impact,
            ])

        # Detailed narrative per upgrade
        for i, u in enumerate(r.upgrades, 1):
            text += (
                f"**{i}. {u.component.replace('_', ' ').title()}**\n\n"
                f"{u.description}\n\n"
                f"- {t('cost', L)}: {_fmt_currency(u.estimated_cost, self.currency)} "
                f"({u.cost_source})\n"
                f"- {t('value_add', L)}: {_fmt_currency(u.estimated_value_add, self.currency)} "
                f"({u.valuation_method})\n"
                f"- {t('roi', L)}: {u.roi_percent:.0f}% | {t('payback', L)}: {u.payback_years:.1f} years "
                f"({u.finance_source})\n"
                f"- {t('energy_saving', L)}: {u.energy_savings_kwh:,.0f} kWh/yr | "
                f"CO₂: {u.co2_reduction_kg:,.0f} kg/yr\n"
                f"- {t('label_impact', L)}: {u.energy_label_impact}\n\n"
            )

        return {"text": text, "tables": [table]}

    # ── 7. Reconciliation (IVS 105) ──

    def _reconciliation(self) -> Dict:
        rec = self.data.reconciliation
        L = self.lang
        text = (
            f"### {t('final_value_opinion', L)}\n\n"
            f"**{t('reconciled_value', L)}:** "
            f"{_fmt_currency(rec.reconciled_value, self.currency) if rec.reconciled_value else t('na', L)}\n\n"
            f"**{t('confidence_level', L)}:** {rec.confidence_level}\n\n"
        )

        # Approach summary table
        table = {
            "headers": [t('approach', L), t('indicated_value', L)],
            "rows": [],
        }
        if rec.cost_approach_value:
            table["rows"].append([t('cost_approach', L), _fmt_currency(rec.cost_approach_value, self.currency)])
        if rec.sales_comparison_value:
            table["rows"].append([t('sales_comparison', L), _fmt_currency(rec.sales_comparison_value, self.currency)])
        if rec.income_approach_value:
            table["rows"].append([t('income_approach', L), _fmt_currency(rec.income_approach_value, self.currency)])

        text += f"**{t('green_premium', L)}:** {_fmt_currency(rec.green_premium_amount, self.currency)}\n\n"
        text += f"**{t('green_premium_basis', L)}:** {rec.green_premium_basis}\n\n"
        text += f"### {t('reconciliation_narrative', L)}\n\n{rec.reconciliation_narrative}\n"

        tables = [table] if table["rows"] else []
        return {"text": text, "tables": tables}

    # ── 8. Assumptions ──

    def _assumptions(self) -> Dict:
        s = self.data.scope
        L = self.lang
        text = f"### {t('general_assumptions', L)}\n\n"
        for a in s.assumptions:
            text += f"- {a}\n"

        if s.special_assumptions:
            text += f"\n### {t('special_assumptions', L)}\n\n"
            for a in s.special_assumptions:
                text += f"- {a}\n"

        if s.departures_from_ivs:
            text += f"\n### {t('departures_from_ivs', L)}\n\n"
            for d in s.departures_from_ivs:
                text += f"- {d}\n"

        text += (
            f"\n### {t('limiting_conditions', L)}\n\n"
            f"- {t('limit_ai_disclaimer', L)}\n"
            f"- {t('limit_no_interior', L)}\n"
            f"- {t('limit_rag_data', L)}\n"
            f"- {t('limit_cost_benchmarks', L)}\n"
            f"- {t('limit_green_premium', L)}\n"
        )
        return {"text": text}

    # ── Appendix A: Detections ──

    def _appendix_detections(self) -> Dict:
        comps = self.data.property_desc.detected_components
        L = self.lang
        if not comps:
            return {"text": f"{t('no_detections', L)}\n"}

        text = (
            f"### {t('yolo_results', L)}\n\n"
            f"{t('yolo_description', L)}\n\n"
        )
        table = {
            "headers": ["#", t('component', L), t('condition', L), t('u_value_header', L), t('area_header', L), t('ai_confidence', L)],
            "rows": [
                [
                    str(i),
                    c.get("type", "—"),
                    c.get("condition", "—"),
                    f"{c['u_value']:.2f}" if c.get("u_value") else "—",
                    f"{c['area']:.1f} m²" if c.get("area") else "—",
                    f"{c['confidence']:.0%}" if c.get("confidence") else "—",
                ]
                for i, c in enumerate(comps, 1)
            ],
        }
        return {"text": text, "tables": [table]}

    # ── Appendix B: Financial Calculations ──

    def _appendix_financials(self) -> Dict:
        upgrades = self.data.renovation.upgrades
        L = self.lang
        if not upgrades:
            return {"text": f"{t('no_financials', L)}\n"}

        text = f"### {t('detailed_financials', L)}\n\n"
        table = {
            "headers": [t('component', L), t('cost', L), t('value_add', L), t('roi', L), t('payback', L), t('kwh_saved', L), t('co2_reduced', L)],
            "rows": [
                [
                    u.component,
                    _fmt_currency(u.estimated_cost, self.currency),
                    _fmt_currency(u.estimated_value_add, self.currency),
                    f"{u.roi_percent:.1f}%",
                    f"{u.payback_years:.1f} yr",
                    f"{u.energy_savings_kwh:,.0f}",
                    f"{u.co2_reduction_kg:,.0f} kg",
                ]
                for u in upgrades
            ],
        }

        # Totals row
        table["rows"].append([
            f"**{t('total', L)}**",
            _fmt_currency(self.data.renovation.total_cost, self.currency),
            _fmt_currency(self.data.renovation.total_value_add, self.currency),
            f"{self.data.renovation.aggregate_roi:.1f}%",
            f"{self.data.renovation.aggregate_payback_years:.1f} yr",
            f"{sum(u.energy_savings_kwh for u in upgrades):,.0f}",
            f"{sum(u.co2_reduction_kg for u in upgrades):,.0f} kg",
        ])

        return {"text": text, "tables": [table]}

    # ── Appendix C: Glossary ──

    def _appendix_glossary(self) -> Dict:
        L = self.lang
        # Use translated glossary based on language
        glossary = list(t_glossary(L))

        # Add custom glossary terms from report data
        for term in self.data.glossary_terms:
            glossary.append((term.get("term", ""), term.get("definition", "")))

        text = f"### {t('glossary_of_terms', L)}\n\n"
        table = {
            "headers": [t('term', L), t('definition', L)],
            "rows": [[trm, dfn] for trm, dfn in sorted(glossary, key=lambda x: x[0])],
        }

        return {"text": text, "tables": [table]}

    # ── Appendix D: Sources & Citations ──

    def _appendix_sources(self) -> Dict:
        L = self.lang
        text = f"### {t('data_sources_citations', L)}\n\n"

        # Standard book references
        standard_refs = [
            ("IVS-Jan-2025", "International Valuation Standards Council",
             "International Valuation Standards (IVS), January 2025 Edition"),
            ("Appraisal-15th", "Appraisal Institute",
             "The Appraisal of Real Estate, 15th Edition"),
            ("Sustainable-Home-Refurbishment", "David Thorpe",
             "Sustainable Home Refurbishment: The Earthscan Expert Guide"),
            ("Green-Building-Illustrated", "Francis D.K. Ching & Ian M. Shapiro",
             "Green Building Illustrated"),
            ("Sustainable-Construction", "Charles J. Kibert",
             "Sustainable Construction: Green Building Design and Delivery"),
            ("Flipping-Houses", "J. Scott",
             "The Book on Flipping Houses: How to Buy, Rehab, and Resell Residential Properties"),
            ("RE-Investor-Cash-Flow", "Frank Gallinelli",
             "What Every Real Estate Investor Needs to Know About Cash Flow"),
            ("REALES", "REALES Institute",
             "REALES: Real Estate Fundamentals"),
        ]

        table = {
            "headers": [t('source_id', L), t('author_publisher', L), t('full_title', L)],
            "rows": [[ref_id, author, title] for ref_id, author, title in standard_refs],
        }

        # Additional sources from report data
        if self.data.data_sources:
            text += f"\n### {t('additional_sources', L)}\n\n"
            for src in self.data.data_sources:
                text += (
                    f"- **{src.get('book_id', '')}**: {src.get('title', '')} "
                    f"— {src.get('section_cited', '')} "
                    f"(Ch. {src.get('chapter', t('na', L))})\n"
                )

        return {"text": text, "tables": [table]}
