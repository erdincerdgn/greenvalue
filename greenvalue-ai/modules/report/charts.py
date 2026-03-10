"""
GreenValue AI — Chart / Visualisation Renderer

Generates publication-quality charts for IVS reports:
  - Energy label gauge (A–G thermometer)
  - ROI waterfall chart
  - Cost breakdown pie chart
  - Heatmap overlay (composites YOLO heatmap on property photo)
  - U-value comparison bar chart

Uses matplotlib with a consistent GreenValue brand palette.
Charts are saved as PNG and embedded in the final PDF.
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("greenvalue-report")

# Try importing matplotlib — graceful fallback if unavailable
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for server use
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.colors import LinearSegmentedColormap
    _MPL_AVAILABLE = True
except ImportError:
    _MPL_AVAILABLE = False
    logger.warning("matplotlib not available — chart generation disabled")

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    _NP_AVAILABLE = False


# ──────────────────────────────────────────────
# Brand Palette
# ──────────────────────────────────────────────

BRAND = {
    "primary": "#2E7D32",      # GreenValue green
    "secondary": "#1B5E20",
    "accent": "#66BB6A",
    "bg": "#FAFAFA",
    "text": "#212121",
    "grid": "#E0E0E0",
}

ENERGY_COLORS = {
    "A": "#00B050",
    "B": "#92D050",
    "C": "#FFFF00",
    "D": "#FFC000",
    "E": "#FF6600",
    "F": "#FF0000",
    "G": "#C00000",
}

ENERGY_LABELS = ["A", "B", "C", "D", "E", "F", "G"]


def _ensure_output_dir(output_dir: Optional[str] = None) -> str:
    """Ensure output directory exists. Default to temp dir."""
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    return tempfile.mkdtemp(prefix="gv_charts_")


class ChartRenderer:
    """
    Renders charts used in IVS-2025 reports.

    All methods are async-compatible but internally synchronous (matplotlib).
    """

    def __init__(self, output_dir: Optional[str] = None, dpi: int = 150):
        self.output_dir = _ensure_output_dir(output_dir)
        self.dpi = dpi

        if _MPL_AVAILABLE:
            # Apply GreenValue style
            plt.rcParams.update({
                "figure.facecolor": BRAND["bg"],
                "axes.facecolor": "#FFFFFF",
                "axes.edgecolor": BRAND["grid"],
                "axes.labelcolor": BRAND["text"],
                "text.color": BRAND["text"],
                "xtick.color": BRAND["text"],
                "ytick.color": BRAND["text"],
                "font.family": "sans-serif",
                "font.size": 10,
            })

    def _save_figure(self, fig: Any, name: str) -> str:
        """Save figure and return the file path."""
        path = os.path.join(self.output_dir, f"{name}.png")
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight", facecolor=BRAND["bg"])
        plt.close(fig)
        logger.debug("Chart saved: %s", path)
        return path

    # ------------------------------------------------------------------
    # Energy Label Gauge
    # ------------------------------------------------------------------

    async def energy_gauge(
        self,
        current_label: str,
        projected_label: str = "",
    ) -> str:
        """
        Render an energy label gauge (vertical thermometer A–G).

        Shows current label with an arrow, and optionally the projected
        label after upgrades.
        """
        if not _MPL_AVAILABLE:
            return ""

        fig, ax = plt.subplots(figsize=(3, 5))

        bar_height = 0.65
        y_positions = list(range(len(ENERGY_LABELS)))

        for i, label in enumerate(ENERGY_LABELS):
            color = ENERGY_COLORS.get(label, "#999999")
            ax.barh(i, 1.0, height=bar_height, color=color, edgecolor="white", linewidth=1)
            ax.text(0.5, i, label, ha="center", va="center",
                    fontsize=16, fontweight="bold", color="white")

        # Current label marker
        current_upper = current_label.upper() if current_label else ""
        if current_upper in ENERGY_LABELS:
            idx = ENERGY_LABELS.index(current_upper)
            ax.annotate(
                "CURRENT",
                xy=(1.0, idx), xytext=(1.6, idx),
                fontsize=9, fontweight="bold", color=BRAND["secondary"],
                arrowprops=dict(arrowstyle="->", color=BRAND["secondary"], lw=2),
                va="center",
            )

        # Projected label marker
        projected_upper = projected_label.upper() if projected_label else ""
        if projected_upper in ENERGY_LABELS and projected_upper != current_upper:
            idx = ENERGY_LABELS.index(projected_upper)
            ax.annotate(
                "AFTER\nUPGRADE",
                xy=(1.0, idx), xytext=(1.6, idx),
                fontsize=8, fontweight="bold", color=BRAND["primary"],
                arrowprops=dict(arrowstyle="->", color=BRAND["primary"], lw=2),
                va="center",
            )

        ax.set_xlim(0, 2.5)
        ax.set_ylim(-0.5, len(ENERGY_LABELS) - 0.5)
        ax.invert_yaxis()
        ax.axis("off")
        ax.set_title("Energy Performance", fontsize=12, fontweight="bold",
                      color=BRAND["text"], pad=10)

        return self._save_figure(fig, "energy_gauge")

    # ------------------------------------------------------------------
    # ROI Waterfall Chart
    # ------------------------------------------------------------------

    async def roi_waterfall(
        self,
        upgrades: List[Any],
        currency: str = "€",
    ) -> str:
        """
        Render a waterfall chart showing cost vs value-add per upgrade.
        """
        if not _MPL_AVAILABLE or not upgrades:
            return ""

        labels = []
        costs = []
        value_adds = []
        for u in upgrades:
            if hasattr(u, "component"):
                labels.append(u.component.replace("_", " ").title())
                costs.append(u.estimated_cost)
                value_adds.append(u.estimated_value_add)
            elif isinstance(u, dict):
                labels.append(u.get("component", "").replace("_", " ").title())
                costs.append(u.get("cost", u.get("estimated_cost", 0)))
                value_adds.append(u.get("value_add", u.get("estimated_value_add", 0)))

        if not labels:
            return ""

        x = list(range(len(labels)))
        width = 0.35

        fig, ax = plt.subplots(figsize=(max(6, len(labels) * 1.8), 5))

        bars_cost = ax.bar(
            [xi - width / 2 for xi in x], costs, width,
            label="Cost", color="#EF5350", alpha=0.85, edgecolor="white"
        )
        bars_value = ax.bar(
            [xi + width / 2 for xi in x], value_adds, width,
            label="Value Add", color=BRAND["primary"], alpha=0.85, edgecolor="white"
        )

        # Value labels on bars
        for bar in bars_cost:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h,
                        f"{currency}{h:,.0f}", ha="center", va="bottom", fontsize=7)
        for bar in bars_value:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h,
                        f"{currency}{h:,.0f}", ha="center", va="bottom", fontsize=7)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel(f"Amount ({currency})")
        ax.set_title("Renovation Cost vs Value Add", fontsize=12, fontweight="bold")
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(axis="y", alpha=0.3)

        return self._save_figure(fig, "roi_waterfall")

    # ------------------------------------------------------------------
    # Cost Breakdown Pie Chart
    # ------------------------------------------------------------------

    async def cost_breakdown_pie(
        self,
        upgrades: List[Any],
        currency: str = "€",
    ) -> str:
        """Render a pie chart showing cost allocation across upgrades."""
        if not _MPL_AVAILABLE or not upgrades:
            return ""

        labels = []
        values = []
        for u in upgrades:
            if hasattr(u, "component"):
                labels.append(u.component.replace("_", " ").title())
                values.append(u.estimated_cost)
            elif isinstance(u, dict):
                labels.append(u.get("component", "").replace("_", " ").title())
                values.append(u.get("cost", u.get("estimated_cost", 0)))

        # Filter out zero-cost items
        filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
        if not filtered:
            return ""
        labels, values = zip(*filtered)

        # Green-based color palette
        greens = ["#1B5E20", "#2E7D32", "#388E3C", "#43A047",
                  "#4CAF50", "#66BB6A", "#81C784", "#A5D6A7"]
        colors = [greens[i % len(greens)] for i in range(len(labels))]

        fig, ax = plt.subplots(figsize=(6, 5))
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.0f%%",
            colors=colors, startangle=90, pctdistance=0.8,
            wedgeprops=dict(edgecolor="white", linewidth=1.5),
        )

        for t in texts:
            t.set_fontsize(8)
        for t in autotexts:
            t.set_fontsize(7)
            t.set_color("white")

        total = sum(values)
        ax.set_title(
            f"Cost Breakdown — Total: {currency}{total:,.0f}",
            fontsize=12, fontweight="bold",
        )

        return self._save_figure(fig, "cost_breakdown")

    # ------------------------------------------------------------------
    # U-Value Comparison Bar Chart
    # ------------------------------------------------------------------

    async def u_value_comparison(
        self,
        components: List[Dict[str, Any]],
    ) -> str:
        """
        Horizontal bar chart: current vs target U-values per component.
        """
        if not _MPL_AVAILABLE or not components:
            return ""

        labels = [c.get("component", "?").replace("_", " ").title() for c in components]
        current = [c.get("u_value_current", 0) for c in components]
        target = [c.get("u_value_target", 0) for c in components]

        y = list(range(len(labels)))
        height = 0.35

        fig, ax = plt.subplots(figsize=(7, max(3, len(labels) * 0.8)))

        ax.barh([yi + height / 2 for yi in y], current, height,
                label="Current", color="#EF5350", alpha=0.8)
        ax.barh([yi - height / 2 for yi in y], target, height,
                label="Target", color=BRAND["primary"], alpha=0.8)

        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("U-Value (W/m²K)")
        ax.set_title("U-Value: Current vs Target", fontsize=12, fontweight="bold")
        ax.legend(loc="lower right", fontsize=9)
        ax.grid(axis="x", alpha=0.3)
        ax.invert_yaxis()

        return self._save_figure(fig, "u_value_comparison")

    # ------------------------------------------------------------------
    # Heatmap Overlay
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Before / After Energy Comparison Bars
    # ------------------------------------------------------------------

    async def before_after_comparison(
        self,
        current_label: str,
        projected_label: str,
        current_heat_loss: float = 0.0,
        projected_heat_loss: float = 0.0,
        current_carbon: float = 0.0,
        projected_carbon: float = 0.0,
    ) -> str:
        """
        Side-by-side bar chart comparing energy performance before
        and after recommended upgrades.
        Shows: energy label rank, heat loss kWh, carbon footprint kg.
        """
        if not _MPL_AVAILABLE or not _NP_AVAILABLE:
            return ""
        if not current_label or not projected_label:
            return ""

        # Map labels to numeric ranks (A=1 best, G=7 worst)
        rank_map = {l: i + 1 for i, l in enumerate(ENERGY_LABELS)}
        cur_rank = rank_map.get(current_label.upper(), 5)
        proj_rank = rank_map.get(projected_label.upper(), 3)

        fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))

        # --- Panel 1: Energy Label Rank ---
        ax = axes[0]
        ax.bar(["Before", "After"], [cur_rank, proj_rank],
               color=[ENERGY_COLORS.get(current_label.upper(), "#999"),
                      ENERGY_COLORS.get(projected_label.upper(), "#999")],
               edgecolor="white", linewidth=1.5, width=0.55)
        ax.set_ylabel("Label Rank (1=A, 7=G)")
        ax.set_ylim(0, 8)
        ax.invert_yaxis()
        for i, (val, lbl) in enumerate(zip(
            [cur_rank, proj_rank], [current_label.upper(), projected_label.upper()]
        )):
            ax.text(i, val + 0.15, lbl, ha="center", va="top",
                    fontsize=14, fontweight="bold", color="white")
        ax.set_title("Energy Label", fontsize=11, fontweight="bold")
        ax.grid(axis="y", alpha=0.2)

        # --- Panel 2: Heat Loss kWh ---
        ax = axes[1]
        if current_heat_loss > 0:
            bars = ax.bar(["Before", "After"],
                          [current_heat_loss, projected_heat_loss],
                          color=["#EF5350", BRAND["primary"]],
                          edgecolor="white", linewidth=1.5, width=0.55)
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, h,
                            f"{h:,.0f}", ha="center", va="bottom", fontsize=8)
            reduction = ((current_heat_loss - projected_heat_loss) / current_heat_loss * 100
                         if current_heat_loss > 0 else 0)
            ax.set_title(f"Heat Loss (kWh/yr)  ↓{reduction:.0f}%",
                         fontsize=11, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "N/A", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="#999")
            ax.set_title("Heat Loss (kWh/yr)", fontsize=11, fontweight="bold")
        ax.grid(axis="y", alpha=0.2)

        # --- Panel 3: Carbon Footprint ---
        ax = axes[2]
        if current_carbon > 0:
            bars = ax.bar(["Before", "After"],
                          [current_carbon, projected_carbon],
                          color=["#EF5350", BRAND["primary"]],
                          edgecolor="white", linewidth=1.5, width=0.55)
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, h,
                            f"{h:,.0f}", ha="center", va="bottom", fontsize=8)
            reduction = ((current_carbon - projected_carbon) / current_carbon * 100
                         if current_carbon > 0 else 0)
            ax.set_title(f"CO₂ (kg/yr)  ↓{reduction:.0f}%",
                         fontsize=11, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "N/A", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="#999")
            ax.set_title("CO₂ (kg/yr)", fontsize=11, fontweight="bold")
        ax.grid(axis="y", alpha=0.2)

        fig.suptitle("Before vs After Upgrades", fontsize=13, fontweight="bold",
                     color=BRAND["text"], y=1.02)
        fig.tight_layout()
        return self._save_figure(fig, "before_after_comparison")

    # ------------------------------------------------------------------
    # Cap Rate Sensitivity Table / Chart
    # ------------------------------------------------------------------

    async def cap_rate_sensitivity(
        self,
        base_noi: float,
        base_cap_rate: float = 0.06,
        currency: str = "€",
    ) -> str:
        """
        Render a cap-rate sensitivity chart.

        Shows how the property value changes as the capitalisation rate
        varies from –2pp to +2pp around the base rate.  Critical for
        Income Approach transparency (IVS 105).
        """
        if not _MPL_AVAILABLE or not _NP_AVAILABLE:
            return ""
        if base_noi <= 0 or base_cap_rate <= 0:
            return ""

        # Generate cap rate range: base ±2 pp in 0.5 pp increments
        offsets = np.arange(-2.0, 2.5, 0.5) / 100  # percentage points → decimal
        cap_rates = [base_cap_rate + o for o in offsets]
        cap_rates = [cr for cr in cap_rates if cr > 0.01]  # exclude unreasonable values
        values = [base_noi / cr for cr in cap_rates]

        fig, ax = plt.subplots(figsize=(8, 4.5))

        colors = []
        for cr in cap_rates:
            if abs(cr - base_cap_rate) < 0.001:
                colors.append(BRAND["primary"])
            else:
                colors.append(BRAND["accent"])

        bars = ax.bar(
            [f"{cr:.1%}" for cr in cap_rates],
            values,
            color=colors,
            edgecolor="white",
            linewidth=1.2,
            width=0.6,
        )

        # Value labels
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{currency}{val:,.0f}",
                ha="center", va="bottom", fontsize=7, fontweight="bold",
            )

        # Highlight base rate
        base_idx = None
        for i, cr in enumerate(cap_rates):
            if abs(cr - base_cap_rate) < 0.001:
                base_idx = i
                break
        if base_idx is not None:
            ax.get_xticklabels()[base_idx].set_color(BRAND["secondary"])
            ax.get_xticklabels()[base_idx].set_fontweight("bold")

        ax.set_xlabel("Capitalisation Rate")
        ax.set_ylabel(f"Property Value ({currency})")
        ax.set_title(
            f"Cap Rate Sensitivity — Base NOI: {currency}{base_noi:,.0f}",
            fontsize=12, fontweight="bold",
        )
        ax.grid(axis="y", alpha=0.3)
        plt.xticks(rotation=30, ha="right", fontsize=8)

        return self._save_figure(fig, "cap_rate_sensitivity")

    # ------------------------------------------------------------------
    # Heatmap Overlay
    # ------------------------------------------------------------------

    async def heatmap_overlay(
        self,
        property_photo_path: Optional[str] = None,
        heatmap_path: Optional[str] = None,
    ) -> str:
        """
        Composite a thermal heatmap over a property photograph.
        If either image is missing, returns empty string.
        """
        if not _MPL_AVAILABLE or not _NP_AVAILABLE:
            return ""

        if not property_photo_path or not heatmap_path:
            return ""

        if not os.path.exists(property_photo_path) or not os.path.exists(heatmap_path):
            logger.warning("Missing image file(s) for heatmap overlay")
            return ""

        try:
            photo = plt.imread(property_photo_path)
            heatmap = plt.imread(heatmap_path)

            fig, axes = plt.subplots(1, 3, figsize=(15, 5))

            # Original photo
            axes[0].imshow(photo)
            axes[0].set_title("Property Photo", fontsize=10, fontweight="bold")
            axes[0].axis("off")

            # Heatmap
            axes[1].imshow(heatmap)
            axes[1].set_title("Thermal Heatmap", fontsize=10, fontweight="bold")
            axes[1].axis("off")

            # Overlay
            axes[2].imshow(photo)
            axes[2].imshow(heatmap, alpha=0.5)
            axes[2].set_title("Overlay", fontsize=10, fontweight="bold")
            axes[2].axis("off")

            fig.suptitle("AI Thermal Analysis", fontsize=13, fontweight="bold",
                         color=BRAND["text"])
            fig.tight_layout()

            return self._save_figure(fig, "heatmap_overlay")

        except Exception as exc:
            logger.warning("Heatmap overlay failed: %s", exc)
            return ""
