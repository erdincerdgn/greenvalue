# ============================================================
# GreenValue AI Engine - Heatmap Generator
# Generates thermal overlay visualizations for property images
# ============================================================

import io
import logging
from typing import Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for Docker
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from PIL import Image

logger = logging.getLogger(__name__)


class HeatmapGenerator:
    """Generate thermal heatmap overlays from YOLO detection results."""

    # Color mapping: Good (blue/green) → Poor (yellow/red)
    CONDITION_COLORS = {
        "good": (0.0, 0.6, 0.2, 0.35),       # Green (semi-transparent)
        "fair": (1.0, 0.8, 0.0, 0.40),        # Yellow
        "poor": (1.0, 0.4, 0.0, 0.50),        # Orange
        "critical": (0.9, 0.1, 0.1, 0.55),    # Red
    }

    # U-Value thresholds for condition rating (W/m²·K)
    UVALUE_THRESHOLDS = {
        "window": {"good": 1.3, "fair": 2.0, "poor": 3.0},
        "facade": {"good": 0.3, "fair": 0.5, "poor": 0.8},
        "roof": {"good": 0.2, "fair": 0.35, "poor": 0.5},
        "door": {"good": 1.8, "fair": 2.5, "poor": 3.5},
    }

    def generate(
        self,
        image: np.ndarray | Image.Image,
        detections: list[dict],
        u_values: Optional[dict] = None,
    ) -> bytes:
        """
        Generate a heatmap overlay on the original image.

        Args:
            image: Original property photo
            detections: List of detection dicts with bbox and mask_polygon
            u_values: Optional dict mapping detection index to U-value

        Returns:
            PNG image bytes of the heatmap overlay
        """
        if isinstance(image, Image.Image):
            image = np.array(image)

        fig, ax = plt.subplots(1, 1, figsize=(12, 8), dpi=100)
        ax.imshow(image)
        ax.set_axis_off()

        for i, detection in enumerate(detections):
            u_value = u_values.get(i) if u_values else None
            condition = self._rate_condition(
                detection.get("class_name", "unknown"),
                u_value,
            )
            color = self.CONDITION_COLORS.get(condition, self.CONDITION_COLORS["fair"])

            # Draw mask polygon overlay
            if "mask_polygon" in detection and len(detection["mask_polygon"]) >= 6:
                polygon = np.array(detection["mask_polygon"]).reshape(-1, 2)
                from matplotlib.patches import Polygon as MplPolygon
                patch = MplPolygon(
                    polygon, closed=True,
                    facecolor=color,
                    edgecolor=color[:3] + (0.8,),
                    linewidth=2,
                )
                ax.add_patch(patch)
            else:
                # Fallback to bounding box
                bbox = detection.get("bbox", {})
                x1, y1 = bbox.get("x_min", 0), bbox.get("y_min", 0)
                x2, y2 = bbox.get("x_max", 0), bbox.get("y_max", 0)
                from matplotlib.patches import Rectangle
                rect = Rectangle(
                    (x1, y1), x2 - x1, y2 - y1,
                    facecolor=color,
                    edgecolor=color[:3] + (0.8,),
                    linewidth=2,
                )
                ax.add_patch(rect)

            # Add label
            bbox = detection.get("bbox", {})
            label_x = bbox.get("x_min", 0)
            label_y = bbox.get("y_min", 0) - 5
            label_text = f"{detection.get('class_name', '?')} | {condition.upper()}"
            if u_value is not None:
                label_text += f" | U={u_value:.2f}"
            ax.text(
                label_x, label_y, label_text,
                color="white", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color[:3] + (0.7,), edgecolor="none"),
            )

        # Add color legend
        self._add_legend(ax)

        plt.tight_layout(pad=0)

        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=100)
        plt.close(fig)
        buf.seek(0)

        logger.info(f"Heatmap generated: {len(detections)} components highlighted")
        return buf.getvalue()

    def _rate_condition(self, component_type: str, u_value: Optional[float]) -> str:
        """Rate building component condition based on U-value."""
        if u_value is None:
            return "fair"

        thresholds = self.UVALUE_THRESHOLDS.get(component_type)
        if thresholds is None:
            return "fair"

        if u_value <= thresholds["good"]:
            return "good"
        elif u_value <= thresholds["fair"]:
            return "fair"
        elif u_value <= thresholds["poor"]:
            return "poor"
        else:
            return "critical"

    def _add_legend(self, ax) -> None:
        """Add a color legend to the heatmap."""
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=self.CONDITION_COLORS["good"][:3], label="Good (Energy Efficient)"),
            Patch(facecolor=self.CONDITION_COLORS["fair"][:3], label="Fair (Minor Issues)"),
            Patch(facecolor=self.CONDITION_COLORS["poor"][:3], label="Poor (Significant Loss)"),
            Patch(facecolor=self.CONDITION_COLORS["critical"][:3], label="Critical (Urgent)"),
        ]
        ax.legend(
            handles=legend_elements,
            loc="lower right",
            fontsize=8,
            framealpha=0.8,
        )
