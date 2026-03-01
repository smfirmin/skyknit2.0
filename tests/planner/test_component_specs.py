"""Tests for planner.component_specs — build_component_spec."""

from __future__ import annotations

from types import MappingProxyType

from skyknit.planner.component_specs import build_component_spec
from skyknit.schemas.garment import ComponentBlueprint, EdgeSpec
from skyknit.schemas.manifest import ComponentSpec, Handedness, ShapeType
from skyknit.topology.types import EdgeType


def _bp(
    name: str, shape: ShapeType, handedness: Handedness, *edges: EdgeSpec
) -> ComponentBlueprint:
    return ComponentBlueprint(
        name=name,
        shape_type=shape,
        handedness=handedness,
        edges=edges,
        dimension_rules=(),
    )


class TestBuildComponentSpec:
    def test_returns_component_spec(self):
        bp = _bp("body", ShapeType.CYLINDER, Handedness.NONE)
        spec = build_component_spec(bp, {"circumference_mm": 914.4, "depth_mm": 457.2})
        assert isinstance(spec, ComponentSpec)

    def test_spec_is_frozen(self):
        import pytest

        bp = _bp("body", ShapeType.CYLINDER, Handedness.NONE)
        spec = build_component_spec(bp, {"circumference_mm": 914.4, "depth_mm": 457.2})
        with pytest.raises(Exception):
            spec.name = "other"  # type: ignore[misc]

    def test_name_from_blueprint(self):
        bp = _bp("yoke", ShapeType.CYLINDER, Handedness.NONE)
        spec = build_component_spec(bp, {})
        assert spec.name == "yoke"

    def test_shape_type_from_blueprint(self):
        bp = _bp("left_sleeve", ShapeType.TRAPEZOID, Handedness.LEFT)
        spec = build_component_spec(bp, {})
        assert spec.shape_type == ShapeType.TRAPEZOID

    def test_handedness_from_blueprint(self):
        bp = _bp("right_sleeve", ShapeType.TRAPEZOID, Handedness.RIGHT)
        spec = build_component_spec(bp, {})
        assert spec.handedness == Handedness.RIGHT

    def test_dimensions_stored_as_mapping_proxy(self):
        bp = _bp("body", ShapeType.CYLINDER, Handedness.NONE)
        spec = build_component_spec(bp, {"circumference_mm": 508.0, "depth_mm": 254.0})
        assert isinstance(spec.dimensions, MappingProxyType)
        assert spec.dimensions["circumference_mm"] == 508.0

    def test_instantiation_count_is_one(self):
        bp = _bp("body", ShapeType.CYLINDER, Handedness.NONE)
        spec = build_component_spec(bp, {})
        assert spec.instantiation_count == 1

    def test_edges_built_from_edge_specs(self):
        bp = _bp(
            "yoke",
            ShapeType.CYLINDER,
            Handedness.NONE,
            EdgeSpec("neck", EdgeType.CAST_ON, None),
            EdgeSpec("body_join", EdgeType.LIVE_STITCH, "j_yoke_body"),
        )
        spec = build_component_spec(bp, {})
        assert len(spec.edges) == 2
        neck = next(e for e in spec.edges if e.name == "neck")
        assert neck.edge_type == EdgeType.CAST_ON
        assert neck.join_ref is None

    def test_edge_join_ref_wired(self):
        bp = _bp(
            "body",
            ShapeType.CYLINDER,
            Handedness.NONE,
            EdgeSpec("top", EdgeType.LIVE_STITCH, "j_yoke_body"),
        )
        spec = build_component_spec(bp, {})
        top = next(e for e in spec.edges if e.name == "top")
        assert top.join_ref == "j_yoke_body"

    def test_no_edges(self):
        bp = _bp("body", ShapeType.CYLINDER, Handedness.NONE)
        spec = build_component_spec(bp, {})
        assert spec.edges == ()

    def test_edge_dimension_key_defaults_to_none(self):
        bp = _bp(
            "body", ShapeType.CYLINDER, Handedness.NONE, EdgeSpec("top", EdgeType.LIVE_STITCH, None)
        )
        spec = build_component_spec(bp, {})
        top = next(e for e in spec.edges if e.name == "top")
        assert top.dimension_key is None

    def test_edge_dimension_key_propagated(self):
        bp = _bp(
            "body",
            ShapeType.CYLINDER,
            Handedness.NONE,
            EdgeSpec("top", EdgeType.LIVE_STITCH, None, "circumference_mm"),
        )
        spec = build_component_spec(bp, {})
        top = next(e for e in spec.edges if e.name == "top")
        assert top.dimension_key == "circumference_mm"
