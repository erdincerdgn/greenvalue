# ============================================================
# GreenValue AI Engine — Test Suite
# ============================================================

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# ── Physics Engine Tests ─────────────────────────────────────

class TestPhysicsEngine:
    """Tests for U-Value calculations and energy labelling."""

    def setup_method(self):
        from modules.physics.u_value import PhysicsEngine
        self.engine = PhysicsEngine()

    def test_calculate_resistance_known_material(self):
        """Conductivity-based R calculation: R = thickness / conductivity."""
        # Brick: lambda = 0.77, thickness = 0.30m → R = 0.30/0.77 ≈ 0.39
        resistance = self.engine.calculate_resistance("brick", 0.30)
        assert 0.35 < resistance < 0.45

    def test_calculate_u_value_facade(self):
        """U-value for a standard facade should be within building code range."""
        result = self.engine.calculate_u_value(
            component_type="facade",
            material="brick",
            thickness_m=0.30,
        )
        assert "u_value" in result
        assert 0.1 < result["u_value"] < 5.0

    def test_calculate_u_value_by_year(self):
        """Older buildings should have higher (worse) U-values."""
        old = self.engine.calculate_u_value(
            component_type="facade", building_year=1950
        )
        new = self.engine.calculate_u_value(
            component_type="facade", building_year=2020
        )
        assert old["u_value"] > new["u_value"]

    def test_energy_label_assignment(self):
        """Energy label should be A-G scale string."""
        label = self.engine.assign_energy_label(0.2)
        assert label in ("A+", "A", "B", "C", "D", "E", "F", "G")

    def test_energy_label_low_is_good(self):
        """Low U-value → good label (A/B), high U-value → bad label (F/G)."""
        good = self.engine.assign_energy_label(0.15)
        bad = self.engine.assign_energy_label(3.0)
        assert good in ("A+", "A", "B")
        assert bad in ("F", "G")

    def test_renovation_roi(self):
        """ROI calculation should return payback years and savings."""
        roi = self.engine.calculate_renovation_roi(
            current_u=2.5,
            target_u=0.3,
            component_area_m2=80.0,
        )
        assert "payback_years" in roi
        assert "annual_savings_eur" in roi
        assert roi["payback_years"] > 0
        assert roi["annual_savings_eur"] > 0

    def test_analyze_components_empty(self):
        """Empty detection list should return zeroed results."""
        result = self.engine.analyze_components([])
        assert result["overall_u_value"] == 0
        assert result["energy_label"] in ("A+", "A")
        assert result["components"] == []

    def test_analyze_components_with_detections(self):
        """Should process detection dicts into component analysis."""
        detections = [
            {
                "class_name": "window",
                "confidence": 0.85,
                "bbox": [100, 100, 200, 200],
            },
            {
                "class_name": "facade",
                "confidence": 0.92,
                "bbox": [0, 0, 500, 500],
            },
        ]
        result = self.engine.analyze_components(detections)
        assert len(result["components"]) == 2
        assert result["overall_u_value"] > 0
        assert result["energy_label"] in ("A+", "A", "B", "C", "D", "E", "F", "G")

    def test_material_database_has_entries(self):
        """Material conductivity database should not be empty."""
        assert len(self.engine.MATERIAL_CONDUCTIVITY) > 10

    def test_unknown_component_type(self):
        """Unknown component types should fall back gracefully."""
        result = self.engine.calculate_u_value(
            component_type="chimney",
            building_year=2000,
        )
        assert "u_value" in result


# ── Heatmap Generator Tests ─────────────────────────────────

class TestHeatmapGenerator:
    """Tests for thermal overlay visualization."""

    def setup_method(self):
        from modules.vision.heatmap import HeatmapGenerator
        self.gen = HeatmapGenerator()

    def test_generate_empty_detections(self):
        """Should handle empty detections gracefully."""
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = self.gen.generate(image, [], {})
        assert isinstance(result, bytes)
        assert len(result) > 0  # Should still produce an image

    def test_generate_with_detections(self):
        """Should produce PNG bytes with detection overlays."""
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = [
            {
                "class_name": "window",
                "confidence": 0.9,
                "bbox": [100, 100, 200, 200],
                "mask": None,
            },
        ]
        u_values = {0: 2.5}
        result = self.gen.generate(image, detections, u_values)
        assert isinstance(result, bytes)
        # PNG magic bytes
        assert result[:4] == b"\x89PNG"

    def test_color_for_u_value(self):
        """Good U-values should be green, bad should be red."""
        good_color = self.gen.get_condition_color(0.2)  # Very good
        bad_color = self.gen.get_condition_color(3.5)   # Very bad
        # Green channel should dominate for good
        assert good_color[1] > good_color[0]  # G > R
        # Red channel should dominate for bad
        assert bad_color[0] > bad_color[1]  # R > G


# ── Inference Engine Tests ───────────────────────────────────

class TestInferenceEngine:
    """Tests for YOLO inference engine (mocked — no real model needed)."""

    def test_class_names_defined(self):
        """CLASS_NAMES should list building components."""
        from modules.vision.inference import YOLOInferenceEngine
        engine = YOLOInferenceEngine.__new__(YOLOInferenceEngine)
        assert "window" in engine.CLASS_NAMES
        assert "facade" in engine.CLASS_NAMES
        assert "roof" in engine.CLASS_NAMES
        assert len(engine.CLASS_NAMES) >= 5

    @patch("modules.vision.inference.YOLO")
    def test_load_model(self, mock_yolo_class):
        """Model loading should instantiate YOLO and move to device."""
        from modules.vision.inference import YOLOInferenceEngine
        mock_model = MagicMock()
        mock_model.model_name = "yolo11n-seg"
        mock_yolo_class.return_value = mock_model

        engine = YOLOInferenceEngine()
        engine.load_model()

        assert engine.model is not None
        mock_yolo_class.assert_called_once()


# ── Settings Tests ───────────────────────────────────────────

class TestSettings:
    """Tests for configuration module."""

    def test_settings_load(self):
        """Settings should load with defaults."""
        from config.settings import Settings
        s = Settings()
        assert s.yolo_model_size in ("n", "s", "m", "l", "x")
        assert s.yolo_img_size > 0
        assert s.yolo_conf_threshold > 0

    def test_resolved_device(self):
        """resolved_device should return 'cpu' or 'cuda:N'."""
        from config.settings import Settings
        s = Settings()
        device = s.resolved_device
        assert device.startswith("cpu") or device.startswith("cuda")

    def test_yolo_model_name_property(self):
        """yolo_model_name should follow format: yolo11{size}-seg."""
        from config.settings import Settings
        s = Settings()
        name = s.yolo_model_name
        assert name.startswith("yolo11")
        assert name.endswith("-seg")


# ── Pipeline Integration Tests (mocked) ─────────────────────

class TestAnalysisPipeline:
    """Integration tests for the analysis pipeline (mocked I/O)."""

    @pytest.mark.asyncio
    @patch("modules.pipeline.get_storage_service")
    @patch("modules.pipeline.get_inference_engine")
    async def test_analyze_image_only(self, mock_engine_fn, mock_storage_fn):
        """analyze_image_only should return detections and physics."""
        from modules.pipeline import AnalysisPipeline

        # Mock inference engine
        mock_engine = MagicMock()
        mock_engine.predict.return_value = {
            "detections": [
                {"class_name": "window", "confidence": 0.9, "bbox": [10, 10, 50, 50]},
            ],
            "inference_time_ms": 42.0,
            "model_version": "yolo11n-seg",
            "device": "cpu",
            "image_metadata": {"width": 640, "height": 480},
        }
        mock_engine_fn.return_value = mock_engine

        # Create a tiny test image (PNG)
        from PIL import Image
        import io

        img = Image.new("RGB", (640, 480), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        pipeline = AnalysisPipeline()
        result = await pipeline.analyze_image_only(image_bytes)

        assert "detections" in result
        assert "physics" in result
        assert result["inference_time_ms"] == 42.0
