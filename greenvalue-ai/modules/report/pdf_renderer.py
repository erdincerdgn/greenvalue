"""
GreenValue AI — PDF Report Renderer (WeasyPrint)

ARCHITECTURE DECISION (v2):
    Ditched ReportLab for Jinja2 + HTML/CSS + WeasyPrint.

    Why:
    - ReportLab forces pixel-level positioning ("go 50px X, 120px Y, write here").
      Changing the report layout means rewriting all Python code.
    - With HTML/CSS you design the report like a web page; tables, images,
      charts, and page breaks are trivial CSS.
    - To change the design later, you only edit an HTML file — you don't
      even touch the Python backend code.

    Stack:
        Jinja2      → template engine  (renders data into HTML)
        Tailwind    → utility-first CSS bundled inline for print
        WeasyPrint  → headless HTML → PDF (no browser needed, pure Python)

Dependencies:
    pip install weasyprint jinja2
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ivs_template import IVSReportData, IVSSection, IVSTemplate

logger = logging.getLogger("greenvalue-report")

# ── Jinja2 is mandatory ──────────────────────────────────────────
try:
    import jinja2
    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False
    logger.error("jinja2 not installed.  pip install jinja2")

# ── WeasyPrint (HTML → PDF) ──────────────────────────────────────
try:
    import weasyprint                       # type: ignore[import-untyped]
    _WEASYPRINT_AVAILABLE = True
except ImportError:
    _WEASYPRINT_AVAILABLE = False
    logger.warning(
        "weasyprint not installed — PDF rendering disabled.  "
        "pip install weasyprint"
    )


# ──────────────────────────────────────────────
# Template directory lives next to this file
# ──────────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).parent / "templates"


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _b64_image(path: str) -> str:
    """Read an image file and return a data-URI for embedding in HTML."""
    if not path or not os.path.exists(path):
        return ""
    try:
        data = Path(path).read_bytes()
        ext = Path(path).suffix.lstrip(".").lower()
        mime = {
            "png": "image/png", "jpg": "image/jpeg",
            "jpeg": "image/jpeg", "svg": "image/svg+xml",
            "webp": "image/webp",
        }.get(ext, "image/png")
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"
    except Exception as exc:
        logger.warning("Cannot read image %s: %s", path, exc)
        return ""


def _fmt_currency(value: float, symbol: str = "€") -> str:
    """Jinja2 filter: format a number as currency."""
    if value is None:
        return f"{symbol}0"
    if abs(value) >= 1_000_000:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.2f}"


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

class PDFRenderer:
    """
    Renders IVSReportData → HTML (Jinja2) → PDF (WeasyPrint).

    Usage:
        renderer = PDFRenderer()
        pdf_bytes = await renderer.render(report_data, sections, config, chart_paths)
    """

    def __init__(self, templates_dir: Optional[str] = None):
        tpl_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        if not tpl_dir.exists():
            tpl_dir.mkdir(parents=True, exist_ok=True)

        if _JINJA2_AVAILABLE:
            self._env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(tpl_dir)),
                autoescape=jinja2.select_autoescape(["html"]),
            )
            # Custom Jinja2 filters
            self._env.filters["currency"] = _fmt_currency
            self._env.filters["b64image"] = _b64_image
        else:
            self._env = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # render() — main entry point (same public API as the old ReportLab version)
    # ------------------------------------------------------------------

    async def render(
        self,
        report_data: IVSReportData,
        sections: List[IVSSection],
        config: Any = None,
        chart_paths: Optional[Dict[str, str]] = None,
    ) -> bytes:
        """
        Render the full report to PDF bytes.

        Pipeline:
            1. Build a template context dict from IVSReportData
            2. Render Jinja2 HTML template  (report.html)
            3. Pass HTML to WeasyPrint → PDF bytes
        """
        if not _JINJA2_AVAILABLE:
            logger.error("Cannot render: jinja2 not installed")
            return b""
        if not _WEASYPRINT_AVAILABLE:
            logger.error("Cannot render: weasyprint not installed")
            return b""

        html = await self._render_html(report_data, sections, config, chart_paths)
        if not html:
            return b""

        # HTML → PDF via WeasyPrint
        try:
            pdf_bytes: bytes = weasyprint.HTML(
                string=html,
                base_url=str(_TEMPLATES_DIR),
            ).write_pdf()
        except Exception as exc:
            logger.error("WeasyPrint PDF generation failed: %s", exc, exc_info=True)
            return b""

        logger.info("PDF rendered: %d bytes, %d sections", len(pdf_bytes), len(sections))
        return pdf_bytes

    # ------------------------------------------------------------------
    # render_html() — useful for browser preview / debug
    # ------------------------------------------------------------------

    async def render_html(
        self,
        report_data: IVSReportData,
        sections: List[IVSSection],
        config: Any = None,
        chart_paths: Optional[Dict[str, str]] = None,
    ) -> str:
        """Return the rendered HTML string (e.g. for a live preview endpoint)."""
        return await self._render_html(report_data, sections, config, chart_paths)

    # ------------------------------------------------------------------
    # Internal: build HTML
    # ------------------------------------------------------------------

    async def _render_html(
        self,
        report_data: IVSReportData,
        sections: List[IVSSection],
        config: Any = None,
        chart_paths: Optional[Dict[str, str]] = None,
    ) -> str:
        if not _JINJA2_AVAILABLE or self._env is None:
            return ""

        chart_paths = chart_paths or {}
        language = getattr(config, "language", "en") if config else "en"
        branding = getattr(config, "branding", {}) if config else {}
        currency = getattr(config, "currency_symbol", "€") if config else "€"

        # ── Build section blocks via SectionGenerator ──
        from .sections import SectionGenerator
        gen = SectionGenerator(report_data, language=language, currency=currency)

        section_blocks: List[Dict[str, Any]] = []
        for section in sections:
            block = gen.generate(section)
            block["section_id"] = section.value
            block["is_appendix"] = section.value.startswith("appendix_")
            section_blocks.append(block)

        # ── Template context ──
        ctx: Dict[str, Any] = {
            # Direct data access
            "report": report_data,
            "cover": report_data.cover,
            "scope": report_data.scope,
            "property": report_data.property_desc,
            "energy": report_data.energy,
            "renovation": report_data.renovation,
            "reconciliation": report_data.reconciliation,
            "valuation_approaches": report_data.valuation_approaches,
            "glossary_terms": report_data.glossary_terms,
            "data_sources": report_data.data_sources,

            # Pre-built section blocks
            "sections": section_blocks,

            # Charts as base64 data-URIs
            "charts": {k: _b64_image(v) for k, v in chart_paths.items()},

            # Embedded images
            "cover_photo": _b64_image(report_data.cover.property_photo_path or ""),
            "heatmap": _b64_image(report_data.energy.heatmap_path or ""),

            # Config
            "language": language,
            "currency": currency,
            "branding": {
                "company_name": branding.get("company_name", "GreenValue AI"),
                "logo_path": branding.get("logo_path", ""),
                "accent_color": branding.get("accent_color", "#2E7D32"),
                "footer_text": branding.get(
                    "footer_text",
                    "Powered by GreenValue AI — IVS 2025 Compliant",
                ),
            },

            # IVS compliance status
            "ivs_warnings": report_data.validate_ivs_compliance(),

            # Helpers exposed to templates
            "fmt_currency": _fmt_currency,
            "IVSTemplate": IVSTemplate,
        }

        # ── Load template ──
        try:
            template = self._env.get_template("report.html")
        except jinja2.TemplateNotFound:
            logger.warning("report.html not found — using inline fallback template")
            template = self._env.from_string(_FALLBACK_TEMPLATE)

        return template.render(**ctx)


# ══════════════════════════════════════════════════════════════════
# Inline fallback template (used when templates/report.html missing)
# In production you would use the file-based template instead.
# ══════════════════════════════════════════════════════════════════

_FALLBACK_TEMPLATE = r"""<!DOCTYPE html>
<html lang="{{ language }}">
<head>
<meta charset="utf-8">
<title>GreenValue Valuation Report — {{ cover.report_number }}</title>
<style>
/* ── Reset & Typography ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  font-size: 10pt; line-height: 1.55; color: #212121;
}
h1 { font-size: 20pt; color: #1B5E20; margin-bottom: 10px; border-bottom: 2px solid #2E7D32; padding-bottom: 6px; }
h2 { font-size: 14pt; color: #2E7D32; margin: 14px 0 6px; }
h3 { font-size: 11pt; color: #333; margin: 10px 0 4px; }
p  { margin: 4px 0; }
ul { margin: 4px 0 4px 20px; }

/* ── Page layout (WeasyPrint) ── */
@page {
  size: A4;
  margin: 22mm 18mm 28mm 18mm;
  @bottom-center {
    content: "{{ branding.footer_text }}  ·  Page " counter(page) " of " counter(pages);
    font-size: 7pt; color: #9e9e9e;
  }
}
.page { page-break-after: always; padding: 0; }
.page:last-child { page-break-after: auto; }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 9pt; }
th { background: #2E7D32; color: #fff; padding: 8px 6px; text-align: left; font-weight: 600; }
td { padding: 6px; border-bottom: 1px solid #e0e0e0; }
tr:nth-child(even) td { background: #f5f5f5; }

/* ── Cover page ── */
.cover { text-align: center; padding-top: 60px; }
.cover h1 { font-size: 30pt; border: none; letter-spacing: 2px; }
.cover .subtitle { color: #757575; font-size: 13pt; margin: 4px 0 30px; }
.cover img.property-photo { max-width: 80%; max-height: 280px; margin: 20px auto; display: block; border-radius: 6px; }
.cover .meta { font-size: 10pt; line-height: 2.2; }
.cover .meta span { color: #757575; }

/* ── Charts / images ── */
.chart-img { max-width: 100%; margin: 14px auto; display: block; }
.heatmap-img { max-width: 100%; margin: 14px 0; border-radius: 4px; }
.label-badge { display: inline-block; padding: 4px 14px; border-radius: 4px; color: #fff; font-weight: bold; font-size: 13pt; }
.label-A, .label-B { background: #2E7D32; }
.label-C { background: #689F38; }
.label-D { background: #FBC02D; color: #333; }
.label-E { background: #F57C00; }
.label-F, .label-G { background: #D32F2F; }

/* ── Warnings ── */
.warn { background: #FFF3E0; border-left: 4px solid #FF9800; padding: 8px 12px; margin: 10px 0; font-size: 9pt; }

/* ── Upgrade cards ── */
.upgrade-card {
  border: 1px solid #C8E6C9; border-radius: 6px;
  padding: 14px; margin: 10px 0; background: #f1f8e9;
}
.upgrade-card h3 { color: #1B5E20; margin-bottom: 6px; }
.upgrade-card .metrics { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 8px; font-size: 9pt; }
.upgrade-card .metric { flex: 1 0 120px; }
.upgrade-card .metric .num { font-size: 14pt; font-weight: bold; color: #2E7D32; }
.upgrade-card .metric .lbl { color: #757575; }
</style>
</head>
<body>

{# ═══════════════ COVER ═══════════════ #}
<div class="page cover">
  <h1>VALUATION REPORT</h1>
  <div class="subtitle">IVS 2025 Compliant — {{ branding.company_name }}</div>
  {% if cover_photo %}<img class="property-photo" src="{{ cover_photo }}" alt="Property Photo">{% endif %}
  <h2 style="border:none;">{{ cover.property_address }}</h2>
  <div class="meta">
    <span>Report №</span> {{ cover.report_number }}<br>
    <span>Report Date</span> {{ cover.report_date }}<br>
    <span>Valuation Date</span> {{ cover.valuation_date }}<br>
    <span>Appraiser</span> {{ cover.appraiser_name }}<br>
    <span>Client</span> {{ cover.client_name or 'N/A' }}<br>
    <span>Intended Use</span> {{ cover.intended_use }}
  </div>
</div>

{# ═══════════════ SECTIONS ═══════════════ #}
{% for sec in sections %}
{% if sec.section_id != 'cover' %}
<div class="page">
  <h1>{{ sec.title }}</h1>

  {# ── Rendered content (basic markdown → HTML) ── #}
  {% for line in sec.content.split('\n') %}
    {% set s = line.strip() %}
    {% if s.startswith('### ') %}<h3>{{ s[4:] }}</h3>
    {% elif s.startswith('## ') %}<h2>{{ s[3:] }}</h2>
    {% elif s.startswith('- ') %}<ul><li>{{ s[2:] }}</li></ul>
    {% elif s.startswith('**') and s.endswith('**') %}<p><strong>{{ s[2:-2] }}</strong></p>
    {% elif s %}<p>{{ s }}</p>
    {% endif %}
  {% endfor %}

  {# ── Tables ── #}
  {% for tbl in sec.tables %}
  <table>
    <thead><tr>{% for h in tbl.headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
    <tbody>
      {% for row in tbl.rows %}
      <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
      {% endfor %}
    </tbody>
  </table>
  {% endfor %}

  {# ── Energy section: gauge + heatmap ── #}
  {% if sec.section_id == 'energy_assessment' %}
    {% if charts.energy_gauge %}
      <img class="chart-img" src="{{ charts.energy_gauge }}" alt="Energy Gauge" style="max-width:220px;">
    {% endif %}
    {% if energy.energy_label_current %}
      <p>Current label:
        <span class="label-badge label-{{ energy.energy_label_current }}">{{ energy.energy_label_current }}</span>
        {% if energy.energy_label_projected %}
        → <span class="label-badge label-{{ energy.energy_label_projected }}">{{ energy.energy_label_projected }}</span>
        {% endif %}
      </p>
    {% endif %}
    {% if heatmap %}
      <img class="heatmap-img" src="{{ heatmap }}" alt="Thermal Heatmap">
    {% endif %}
  {% endif %}

  {# ── Renovation section: upgrade cards + charts ── #}
  {% if sec.section_id == 'renovation_impact' %}
    {% for u in renovation.upgrades %}
    <div class="upgrade-card">
      <h3>{{ u.component }} — {{ u.description }}</h3>
      <div class="metrics">
        <div class="metric"><div class="num">{{ fmt_currency(u.estimated_cost, currency) }}</div><div class="lbl">Cost</div></div>
        <div class="metric"><div class="num">{{ fmt_currency(u.estimated_value_add, currency) }}</div><div class="lbl">Value Add</div></div>
        <div class="metric"><div class="num">{{ '%.1f'|format(u.roi_percent) }}%</div><div class="lbl">ROI</div></div>
        <div class="metric"><div class="num">{{ '%.1f'|format(u.payback_years) }} yr</div><div class="lbl">Payback</div></div>
        <div class="metric"><div class="num">{{ '%.0f'|format(u.energy_savings_kwh) }} kWh</div><div class="lbl">Savings/yr</div></div>
      </div>
      {% if u.valuation_method %}<p style="font-size:8pt;color:#757575;margin-top:6px;">Method: {{ u.valuation_method }}</p>{% endif %}
    </div>
    {% endfor %}

    {% if charts.roi_waterfall %}
      <img class="chart-img" src="{{ charts.roi_waterfall }}" alt="ROI Waterfall Chart">
    {% endif %}
    {% if charts.cost_breakdown %}
      <img class="chart-img" src="{{ charts.cost_breakdown }}" alt="Cost Breakdown Chart">
    {% endif %}
  {% endif %}

  {# ── Reconciliation section: value summary ── #}
  {% if sec.section_id == 'reconciliation' %}
    {% if reconciliation.reconciled_value %}
    <div style="text-align:center;margin:20px 0;padding:16px;background:#E8F5E9;border-radius:8px;">
      <div style="font-size:10pt;color:#757575;">Reconciled Market Value (IVS 104)</div>
      <div style="font-size:26pt;font-weight:bold;color:#1B5E20;">
        {{ fmt_currency(reconciliation.reconciled_value, currency) }}
      </div>
      <div style="font-size:9pt;color:#757575;">Confidence: {{ reconciliation.confidence_level }}</div>
    </div>
    {% endif %}
  {% endif %}
</div>
{% endif %}
{% endfor %}

{# ═══════════════ IVS COMPLIANCE WARNINGS ═══════════════ #}
{% if ivs_warnings %}
<div class="page">
  <h1>IVS Compliance Notes</h1>
  {% for w in ivs_warnings %}
  <div class="warn">⚠ {{ w }}</div>
  {% endfor %}
</div>
{% endif %}

</body>
</html>"""
