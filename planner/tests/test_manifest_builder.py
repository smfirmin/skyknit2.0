"""Tests for planner.manifest_builder — build_shape_manifest."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from planner.garments.v1_yoke_pullover import make_v1_yoke_pullover
from planner.manifest_builder import build_shape_manifest
from schemas.manifest import ShapeManifest
from schemas.proportion import PrecisionPreference, ProportionSpec
from validator.phase1 import validate_phase1

GARMENT_SPEC = make_v1_yoke_pullover()

PROPORTION_SPEC = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
    precision=PrecisionPreference.MEDIUM,
)

MEASUREMENTS = {
    "chest_circumference_mm": 914.4,
    "body_length_mm": 457.2,
    "yoke_depth_mm": 203.2,
    "sleeve_length_mm": 495.3,
    "upper_arm_circumference_mm": 381.0,
    "wrist_circumference_mm": 152.4,
}


class TestBuildShapeManifest:
    def test_returns_shape_manifest(self):
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        assert isinstance(manifest, ShapeManifest)

    def test_component_count(self):
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        assert len(manifest.components) == 4

    def test_component_names_and_order(self):
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        names = [c.name for c in manifest.components]
        assert names == ["yoke", "body", "left_sleeve", "right_sleeve"]

    def test_join_count(self):
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        assert len(manifest.joins) == 1

    def test_join_id(self):
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        assert manifest.joins[0].id == "j_yoke_body"

    def test_yoke_and_body_have_same_circumference(self):
        """Ensures yoke → body CONTINUATION join stitch counts will match."""
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        yoke = next(c for c in manifest.components if c.name == "yoke")
        body = next(c for c in manifest.components if c.name == "body")
        assert yoke.dimensions["circumference_mm"] == pytest.approx(
            body.dimensions["circumference_mm"]
        )

    def test_sleeve_dimensions_computed(self):
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        left = next(c for c in manifest.components if c.name == "left_sleeve")
        assert left.dimensions["top_circumference_mm"] == pytest.approx(381.0 * 1.1)
        assert left.dimensions["bottom_circumference_mm"] == pytest.approx(152.4 * 1.05)
        assert left.dimensions["depth_mm"] == pytest.approx(495.3)

    def test_left_and_right_sleeve_identical_dimensions(self):
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        left = next(c for c in manifest.components if c.name == "left_sleeve")
        right = next(c for c in manifest.components if c.name == "right_sleeve")
        assert dict(left.dimensions) == pytest.approx(dict(right.dimensions))

    def test_missing_measurement_raises_value_error(self):
        bad_measurements = {k: v for k, v in MEASUREMENTS.items() if k != "yoke_depth_mm"}
        with pytest.raises(ValueError, match="yoke_depth_mm"):
            build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, bad_measurements)

    def test_manifest_passes_validate_phase1(self):
        """Integration: produced manifest must pass Phase 1 geometric validation."""
        manifest = build_shape_manifest(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        result = validate_phase1(manifest)
        assert result.passed is True, f"validate_phase1 failed: {result.errors}"
