"""Tests for planner.dimensions — compute_dimensions."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from planner.dimensions import compute_dimensions
from schemas.garment import ComponentBlueprint, DimensionRule, EdgeSpec
from schemas.manifest import Handedness, ShapeType
from schemas.proportion import PrecisionPreference, ProportionSpec
from topology.types import EdgeType

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


def _blueprint(name: str, *rules: DimensionRule) -> ComponentBlueprint:
    return ComponentBlueprint(
        name=name,
        shape_type=ShapeType.CYLINDER,
        handedness=Handedness.NONE,
        edges=(EdgeSpec("top", EdgeType.LIVE_STITCH),),
        dimension_rules=rules,
    )


class TestComputeDimensions:
    def test_direct_measurement_no_ratio(self):
        bp = _blueprint("body", DimensionRule("depth_mm", "body_length_mm"))
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert dims["depth_mm"] == pytest.approx(457.2)

    def test_measurement_times_ratio(self):
        bp = _blueprint(
            "body",
            DimensionRule("circumference_mm", "chest_circumference_mm", "body_ease"),
        )
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert dims["circumference_mm"] == pytest.approx(914.4 * 1.08)

    def test_missing_ratio_key_uses_default(self):
        bp = _blueprint(
            "body",
            DimensionRule("circumference_mm", "chest_circumference_mm", "nonexistent_ease", 1.05),
        )
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert dims["circumference_mm"] == pytest.approx(914.4 * 1.05)

    def test_missing_ratio_key_default_one(self):
        bp = _blueprint(
            "body",
            DimensionRule("circumference_mm", "chest_circumference_mm", "nonexistent_ease"),
        )
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert dims["circumference_mm"] == pytest.approx(914.4 * 1.0)

    def test_multiple_rules_all_applied(self):
        bp = _blueprint(
            "yoke",
            DimensionRule("circumference_mm", "chest_circumference_mm", "body_ease"),
            DimensionRule("depth_mm", "yoke_depth_mm"),
        )
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert set(dims.keys()) == {"circumference_mm", "depth_mm"}
        assert dims["depth_mm"] == pytest.approx(203.2)

    def test_sleeve_top_circumference(self):
        bp = _blueprint(
            "left_sleeve",
            DimensionRule("top_circumference_mm", "upper_arm_circumference_mm", "sleeve_ease"),
            DimensionRule("bottom_circumference_mm", "wrist_circumference_mm", "wrist_ease"),
            DimensionRule("depth_mm", "sleeve_length_mm"),
        )
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert dims["top_circumference_mm"] == pytest.approx(381.0 * 1.1)
        assert dims["bottom_circumference_mm"] == pytest.approx(152.4 * 1.05)
        assert dims["depth_mm"] == pytest.approx(495.3)

    def test_missing_measurement_raises_value_error(self):
        bp = _blueprint("body", DimensionRule("depth_mm", "missing_key"))
        with pytest.raises(ValueError, match="missing_key"):
            compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)

    def test_error_message_names_component(self):
        bp = _blueprint("yoke", DimensionRule("depth_mm", "missing_key"))
        with pytest.raises(ValueError, match="yoke"):
            compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)

    def test_returns_plain_dict(self):
        bp = _blueprint("body", DimensionRule("depth_mm", "body_length_mm"))
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert isinstance(dims, dict)

    def test_no_rules_returns_empty_dict(self):
        bp = _blueprint("empty")
        dims = compute_dimensions(bp, PROPORTION_SPEC, MEASUREMENTS)
        assert dims == {}
