# ============================================================
# GreenValue AI Engine - Physics Engine (U-Value Calculator)
# Thermal transmittance calculations for building components
# ============================================================

import logging
from typing import Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================
# Material Thermal Conductivity Database (λ values in W/m·K)
# ============================================================
THERMAL_CONDUCTIVITY = {
    # Glass types
    "single_glass": 5.8,
    "double_glass": 2.8,
    "double_glass_low_e": 1.6,
    "triple_glass": 0.8,
    "triple_glass_low_e": 0.6,

    # Wall materials
    "brick": 0.84,
    "concrete": 1.75,
    "aerated_concrete": 0.16,
    "limestone": 1.50,
    "wood": 0.15,
    "steel": 50.0,

    # Insulation materials
    "eps_foam": 0.035,
    "xps_foam": 0.030,
    "mineral_wool": 0.040,
    "polyurethane": 0.025,
    "cellulose": 0.040,

    # Roofing
    "clay_tile": 1.00,
    "concrete_tile": 1.50,
    "metal_sheet": 50.0,
    "slate": 2.00,
}

# Standard U-Values by component age (W/m²·K) — European building stock reference
STANDARD_UVALUES = {
    "window": {
        "pre_1970": 5.0,
        "1970_1990": 3.0,
        "1990_2010": 1.8,
        "post_2010": 1.1,
    },
    "facade": {
        "pre_1970": 1.5,
        "1970_1990": 0.8,
        "1990_2010": 0.4,
        "post_2010": 0.2,
    },
    "roof": {
        "pre_1970": 1.2,
        "1970_1990": 0.6,
        "1990_2010": 0.3,
        "post_2010": 0.15,
    },
    "door": {
        "pre_1970": 3.5,
        "1970_1990": 2.5,
        "1990_2010": 1.8,
        "post_2010": 1.3,
    },
    "floor": {
        "pre_1970": 1.0,
        "1970_1990": 0.6,
        "1990_2010": 0.35,
        "post_2010": 0.2,
    },
}

# Energy Label Thresholds (kWh/m²/year) — European standard
ENERGY_LABELS = {
    "A": (0, 50),
    "B": (50, 100),
    "C": (100, 150),
    "D": (150, 200),
    "E": (200, 250),
    "F": (250, 300),
    "G": (300, float("inf")),
}

# Renovation cost estimates per m² (EUR) — typical European market
RENOVATION_COSTS = {
    "window": {"replacement": 350, "improvement": 150},
    "facade": {"full_insulation": 120, "partial_insulation": 60},
    "roof": {"full_insulation": 100, "partial_insulation": 50},
    "door": {"replacement": 500, "improvement": 200},
    "floor": {"insulation": 80},
}


@dataclass
class ComponentAnalysis:
    """Analysis result for a single building component."""
    component_type: str
    area_m2: float
    u_value: float
    heat_loss_w: float
    condition: str
    annual_heat_loss_kwh: float


@dataclass
class RenovationProposal:
    """Renovation proposal with ROI calculations."""
    projected_u_value: float
    projected_energy_label: str
    estimated_cost_eur: float
    annual_savings_eur: float
    payback_years: float
    roi_percentage: float
    recommended_actions: list[str]


class PhysicsEngine:
    """
    Calculates U-Values (thermal transmittance) and energy efficiency metrics.

    Based on EN ISO 6946 standard for thermal resistance of building components.
    """

    # Standard surface resistances (m²·K/W)
    RSI_INTERNAL = 0.13   # Internal surface resistance
    RSE_EXTERNAL = 0.04   # External surface resistance

    # Reference heating season parameters (Central Europe)
    HEATING_DEGREE_DAYS = 3000     # Typical for Central/Northern Europe
    ENERGY_PRICE_EUR_KWH = 0.10   # Average EU energy price

    def calculate_u_value(
        self,
        material: str,
        thickness_mm: float,
        year_installed: Optional[int] = None,
    ) -> float:
        """
        Calculate U-Value for a single layer component.

        U = 1 / (Rsi + R_layer + Rse)
        R_layer = thickness / λ

        Args:
            material: Material type key
            thickness_mm: Material thickness in millimeters
            year_installed: Year of installation (for age-based estimation)

        Returns:
            U-Value in W/m²·K
        """
        conductivity = THERMAL_CONDUCTIVITY.get(material)

        if conductivity is None and material in ("window", "door"):
            # Windows/doors use direct U-values, not layer calculation
            return self._estimate_by_age(material, year_installed)

        if conductivity is None:
            logger.warning(f"Unknown material: {material}, using default brick U-Value")
            conductivity = THERMAL_CONDUCTIVITY["brick"]

        thickness_m = thickness_mm / 1000.0
        r_layer = thickness_m / conductivity
        r_total = self.RSI_INTERNAL + r_layer + self.RSE_EXTERNAL
        u_value = 1.0 / r_total

        return round(u_value, 3)

    def estimate_u_value_from_detection(
        self,
        component_type: str,
        confidence: float,
        year_estimate: Optional[int] = None,
    ) -> float:
        """
        Estimate U-Value from YOLO detection when exact material is unknown.
        Uses visual confidence and heuristic age estimation.
        """
        u_value = self._estimate_by_age(component_type, year_estimate)

        # Adjust based on detection confidence
        # Lower confidence → more uncertain → use conservative (worse) estimate
        uncertainty_factor = 1.0 + (1.0 - confidence) * 0.2
        adjusted = u_value * uncertainty_factor

        return round(adjusted, 3)

    def calculate_heat_loss(
        self,
        u_value: float,
        area_m2: float,
        delta_t: float = 20.0,
    ) -> float:
        """
        Calculate instantaneous heat loss through a component.

        Q = U × A × ΔT (Watts)

        Args:
            u_value: Thermal transmittance (W/m²·K)
            area_m2: Component area in square meters
            delta_t: Temperature difference indoor/outdoor (K)

        Returns:
            Heat loss in Watts
        """
        return round(u_value * area_m2 * delta_t, 2)

    def calculate_annual_heat_loss(
        self,
        u_value: float,
        area_m2: float,
    ) -> float:
        """
        Calculate annual heat loss in kWh using Heating Degree Days.

        Q_annual = U × A × HDD × 24 / 1000

        Returns:
            Annual heat loss in kWh
        """
        q_annual = u_value * area_m2 * self.HEATING_DEGREE_DAYS * 24 / 1000
        return round(q_annual, 2)

    def analyze_components(
        self,
        detections: list[dict],
        pixel_to_m2_ratio: float = 0.001,
    ) -> dict:
        """
        Full analysis pipeline: detections → U-Values → Energy Label → ROI.

        Args:
            detections: List of YOLO detection dicts
            pixel_to_m2_ratio: Conversion factor from pixel area to m²

        Returns:
            Complete analysis result with U-values, energy label, and renovation proposal
        """
        components = []
        total_heat_loss_kwh = 0.0
        total_area = 0.0

        for i, det in enumerate(detections):
            comp_type = det.get("class_name", "unknown")
            area_pixels = det.get("area_pixels", 0)
            area_m2 = max(area_pixels * pixel_to_m2_ratio, 0.5)  # Min 0.5 m²
            confidence = det.get("confidence", 0.5)

            u_value = self.estimate_u_value_from_detection(comp_type, confidence)
            heat_loss = self.calculate_annual_heat_loss(u_value, area_m2)
            condition = self._rate_condition(comp_type, u_value)

            component = ComponentAnalysis(
                component_type=comp_type,
                area_m2=round(area_m2, 2),
                u_value=u_value,
                heat_loss_w=self.calculate_heat_loss(u_value, area_m2),
                condition=condition,
                annual_heat_loss_kwh=heat_loss,
            )
            components.append(component)
            total_heat_loss_kwh += heat_loss
            total_area += area_m2

        # Overall U-Value (area-weighted average)
        if total_area > 0:
            overall_u = sum(c.u_value * c.area_m2 for c in components) / total_area
        else:
            overall_u = 0.0

        # Energy label based on total heat loss per m²
        estimated_floor_area = max(total_area * 2.5, 50)  # Rough floor area estimate
        kwh_per_m2 = total_heat_loss_kwh / estimated_floor_area if estimated_floor_area > 0 else 0
        energy_label = self._classify_energy_label(kwh_per_m2)

        # Annual energy cost
        annual_cost = total_heat_loss_kwh * self.ENERGY_PRICE_EUR_KWH

        # Renovation proposal
        renovation = self._calculate_renovation_roi(components, energy_label, annual_cost)

        return {
            "components": [
                {
                    "component_type": c.component_type,
                    "area_m2": c.area_m2,
                    "u_value": c.u_value,
                    "heat_loss_w": c.heat_loss_w,
                    "condition": c.condition,
                    "annual_heat_loss_kwh": c.annual_heat_loss_kwh,
                    "heat_loss_percentage": round(
                        (c.annual_heat_loss_kwh / total_heat_loss_kwh * 100)
                        if total_heat_loss_kwh > 0 else 0, 1
                    ),
                }
                for c in components
            ],
            "overall_u_value": round(overall_u, 3),
            "energy_label": energy_label,
            "total_annual_heat_loss_kwh": round(total_heat_loss_kwh, 2),
            "annual_energy_cost_eur": round(annual_cost, 2),
            "renovation": renovation,
        }

    def _estimate_by_age(self, component_type: str, year: Optional[int] = None) -> float:
        """Estimate U-Value based on component age."""
        standards = STANDARD_UVALUES.get(component_type, STANDARD_UVALUES.get("facade", {}))

        if year is None:
            # Default to 1990-2010 era (most common existing building stock)
            return standards.get("1990_2010", 1.0)

        if year < 1970:
            return standards.get("pre_1970", 2.0)
        elif year < 1990:
            return standards.get("1970_1990", 1.0)
        elif year < 2010:
            return standards.get("1990_2010", 0.5)
        else:
            return standards.get("post_2010", 0.3)

    def _rate_condition(self, component_type: str, u_value: float) -> str:
        """Rate component condition based on U-value thresholds."""
        thresholds = {
            "window": {"good": 1.3, "fair": 2.0, "poor": 3.0},
            "facade": {"good": 0.3, "fair": 0.5, "poor": 0.8},
            "roof": {"good": 0.2, "fair": 0.35, "poor": 0.5},
            "door": {"good": 1.8, "fair": 2.5, "poor": 3.5},
        }
        t = thresholds.get(component_type, {"good": 0.5, "fair": 1.0, "poor": 2.0})

        if u_value <= t["good"]:
            return "good"
        elif u_value <= t["fair"]:
            return "fair"
        elif u_value <= t["poor"]:
            return "poor"
        return "critical"

    def _classify_energy_label(self, kwh_per_m2: float) -> str:
        """Classify energy label based on kWh/m²/year."""
        for label, (low, high) in ENERGY_LABELS.items():
            if low <= kwh_per_m2 < high:
                return label
        return "G"

    def _calculate_renovation_roi(
        self,
        components: list[ComponentAnalysis],
        current_label: str,
        current_annual_cost: float,
    ) -> dict:
        """Calculate renovation ROI based on upgrading all poor/critical components."""
        total_cost = 0.0
        actions = []
        projected_heat_loss = 0.0

        for c in components:
            if c.condition in ("poor", "critical"):
                # Get renovation cost
                cost_data = RENOVATION_COSTS.get(c.component_type, {})
                cost = cost_data.get("replacement", cost_data.get("full_insulation", 100))
                total_cost += cost * c.area_m2

                # Project improved U-value (post-2010 standard)
                new_u = self._estimate_by_age(c.component_type, 2020)
                projected_heat_loss += self.calculate_annual_heat_loss(new_u, c.area_m2)

                actions.append(
                    f"Upgrade {c.component_type} ({c.area_m2} m²): "
                    f"U-value {c.u_value} → {new_u} W/m²·K"
                )
            else:
                projected_heat_loss += c.annual_heat_loss_kwh

        projected_cost = projected_heat_loss * self.ENERGY_PRICE_EUR_KWH
        annual_savings = max(current_annual_cost - projected_cost, 0)
        payback = total_cost / annual_savings if annual_savings > 0 else 999
        roi = (annual_savings / total_cost * 100) if total_cost > 0 else 0

        # Project new energy label
        total_area_estimate = sum(c.area_m2 for c in components) * 2.5
        if total_area_estimate > 0:
            projected_kwh_m2 = projected_heat_loss / max(total_area_estimate, 50)
        else:
            projected_kwh_m2 = 0
        projected_label = self._classify_energy_label(projected_kwh_m2)

        return {
            "projected_u_value": round(
                projected_heat_loss / max(sum(c.area_m2 for c in components), 1) /
                self.HEATING_DEGREE_DAYS / 24 * 1000, 3
            ) if components else 0,
            "projected_energy_label": projected_label,
            "estimated_cost_eur": round(total_cost, 2),
            "annual_savings_eur": round(annual_savings, 2),
            "payback_years": round(payback, 1),
            "roi_percentage": round(roi, 1),
            "recommended_actions": actions,
        }
