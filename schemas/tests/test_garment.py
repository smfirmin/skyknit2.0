"""Tests for schemas.garment — GarmentSpec and supporting types."""

from __future__ import annotations

import pytest

from schemas.garment import (
    ComponentBlueprint,
    DimensionRule,
    EdgeSpec,
    GarmentSpec,
    JoinSpec,
)
from schemas.manifest import Handedness, ShapeType
from topology.types import EdgeType, JoinType


class TestEdgeSpec:
    def test_is_frozen(self):
        es = EdgeSpec(name="top", edge_type=EdgeType.LIVE_STITCH, join_id="j1")
        with pytest.raises(Exception):
            es.name = "bottom"  # type: ignore[misc]

    def test_join_id_defaults_to_none(self):
        es = EdgeSpec(name="hem", edge_type=EdgeType.BOUND_OFF)
        assert es.join_id is None

    def test_fields_accessible(self):
        es = EdgeSpec(name="top", edge_type=EdgeType.CAST_ON, join_id="j2")
        assert es.name == "top"
        assert es.edge_type == EdgeType.CAST_ON
        assert es.join_id == "j2"


class TestDimensionRule:
    def test_is_frozen(self):
        dr = DimensionRule(
            dimension_key="circumference_mm", measurement_key="chest_circumference_mm"
        )
        with pytest.raises(Exception):
            dr.dimension_key = "depth_mm"  # type: ignore[misc]

    def test_ratio_key_defaults_to_none(self):
        dr = DimensionRule(dimension_key="depth_mm", measurement_key="body_length_mm")
        assert dr.ratio_key is None

    def test_default_ratio_is_one(self):
        dr = DimensionRule(dimension_key="depth_mm", measurement_key="body_length_mm")
        assert dr.default_ratio == 1.0

    def test_explicit_ratio_key(self):
        dr = DimensionRule(
            dimension_key="circumference_mm",
            measurement_key="chest_circumference_mm",
            ratio_key="body_ease",
            default_ratio=1.08,
        )
        assert dr.ratio_key == "body_ease"
        assert dr.default_ratio == 1.08


class TestComponentBlueprint:
    def test_is_frozen(self):
        bp = ComponentBlueprint(
            name="body",
            shape_type=ShapeType.CYLINDER,
            handedness=Handedness.NONE,
            edges=(EdgeSpec(name="top", edge_type=EdgeType.LIVE_STITCH),),
            dimension_rules=(DimensionRule("circumference_mm", "chest_circumference_mm"),),
        )
        with pytest.raises(Exception):
            bp.name = "yoke"  # type: ignore[misc]

    def test_fields_accessible(self):
        bp = ComponentBlueprint(
            name="left_sleeve",
            shape_type=ShapeType.TRAPEZOID,
            handedness=Handedness.LEFT,
            edges=(),
            dimension_rules=(),
        )
        assert bp.name == "left_sleeve"
        assert bp.shape_type == ShapeType.TRAPEZOID
        assert bp.handedness == Handedness.LEFT


class TestJoinSpec:
    def test_is_frozen(self):
        js = JoinSpec(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="yoke.body_join",
            edge_b_ref="body.top",
        )
        with pytest.raises(Exception):
            js.id = "j2"  # type: ignore[misc]

    def test_fields_accessible(self):
        js = JoinSpec(
            id="j_sleeve",
            join_type=JoinType.HELD_STITCH,
            edge_a_ref="body.armhole",
            edge_b_ref="sleeve.top",
        )
        assert js.id == "j_sleeve"
        assert js.join_type == JoinType.HELD_STITCH
        assert js.edge_a_ref == "body.armhole"
        assert js.edge_b_ref == "sleeve.top"


class TestGarmentSpec:
    def _make_spec(self) -> GarmentSpec:
        bp = ComponentBlueprint(
            name="body",
            shape_type=ShapeType.CYLINDER,
            handedness=Handedness.NONE,
            edges=(
                EdgeSpec("top", EdgeType.LIVE_STITCH),
                EdgeSpec("hem", EdgeType.BOUND_OFF),
            ),
            dimension_rules=(
                DimensionRule("circumference_mm", "chest_circumference_mm", "body_ease"),
                DimensionRule("depth_mm", "body_length_mm"),
            ),
        )
        return GarmentSpec(
            garment_type="test-garment",
            components=(bp,),
            joins=(),
            required_measurements=frozenset({"chest_circumference_mm", "body_length_mm"}),
        )

    def test_is_frozen(self):
        spec = self._make_spec()
        with pytest.raises(Exception):
            spec.garment_type = "other"  # type: ignore[misc]

    def test_required_measurements_is_frozenset(self):
        spec = self._make_spec()
        assert isinstance(spec.required_measurements, frozenset)

    def test_components_tuple(self):
        spec = self._make_spec()
        assert len(spec.components) == 1
        assert spec.components[0].name == "body"

    def test_joins_empty(self):
        spec = self._make_spec()
        assert spec.joins == ()
