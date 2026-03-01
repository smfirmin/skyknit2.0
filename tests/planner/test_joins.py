"""Tests for planner.joins — build_join and build_all_joins."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from skyknit.planner.joins import build_all_joins, build_join
from skyknit.schemas.garment import JoinSpec
from skyknit.schemas.manifest import ComponentSpec, Handedness, ShapeType
from skyknit.topology.types import Edge, EdgeType, Join, JoinType


def _spec(name: str, *edges: Edge) -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": 508.0, "depth_mm": 254.0},
        edges=tuple(edges),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


YOKE_SPEC = _spec(
    "yoke",
    Edge("neck", EdgeType.CAST_ON),
    Edge("body_join", EdgeType.LIVE_STITCH, join_ref="j_yoke_body"),
)
BODY_SPEC = _spec(
    "body",
    Edge("top", EdgeType.LIVE_STITCH, join_ref="j_yoke_body"),
    Edge("hem", EdgeType.BOUND_OFF),
)
COMPONENT_SPECS = {"yoke": YOKE_SPEC, "body": BODY_SPEC}


class TestBuildJoin:
    def test_returns_join(self):
        js = JoinSpec("j1", JoinType.CONTINUATION, "yoke.body_join", "body.top")
        result = build_join(js, COMPONENT_SPECS)
        assert isinstance(result, Join)

    def test_join_id_preserved(self):
        js = JoinSpec("j_yoke_body", JoinType.CONTINUATION, "yoke.body_join", "body.top")
        result = build_join(js, COMPONENT_SPECS)
        assert result.id == "j_yoke_body"

    def test_join_type_preserved(self):
        js = JoinSpec("j1", JoinType.CONTINUATION, "yoke.body_join", "body.top")
        result = build_join(js, COMPONENT_SPECS)
        assert result.join_type == JoinType.CONTINUATION

    def test_edge_refs_preserved(self):
        js = JoinSpec("j1", JoinType.CONTINUATION, "yoke.body_join", "body.top")
        result = build_join(js, COMPONENT_SPECS)
        assert result.edge_a_ref == "yoke.body_join"
        assert result.edge_b_ref == "body.top"

    def test_continuation_has_empty_parameters(self):
        """CONTINUATION has no defaults in the registry."""
        js = JoinSpec("j1", JoinType.CONTINUATION, "yoke.body_join", "body.top")
        result = build_join(js, COMPONENT_SPECS)
        assert dict(result.parameters) == {}

    def test_parameters_is_mapping_proxy(self):
        js = JoinSpec("j1", JoinType.CONTINUATION, "yoke.body_join", "body.top")
        result = build_join(js, COMPONENT_SPECS)
        assert isinstance(result.parameters, MappingProxyType)

    def test_pickup_join_gets_registry_defaults(self):
        """BOUND_OFF → LIVE_STITCH via PICKUP should pick up defaults from registry."""
        bound_spec = _spec("src", Edge("sel", EdgeType.BOUND_OFF))
        live_spec = _spec("dst", Edge("top", EdgeType.LIVE_STITCH))
        specs = {"src": bound_spec, "dst": live_spec}
        js = JoinSpec("j_pickup", JoinType.PICKUP, "src.sel", "dst.top")
        result = build_join(js, specs)
        # Registry default for BOUND_OFF → LIVE_STITCH via PICKUP = pickup_ratio + pickup_direction
        assert "pickup_ratio" in result.parameters
        assert "pickup_direction" in result.parameters

    def test_bad_component_name_raises(self):
        js = JoinSpec("j1", JoinType.CONTINUATION, "nonexistent.edge", "body.top")
        with pytest.raises(ValueError, match="nonexistent"):
            build_join(js, COMPONENT_SPECS)

    def test_bad_edge_name_raises(self):
        js = JoinSpec("j1", JoinType.CONTINUATION, "yoke.nonexistent_edge", "body.top")
        with pytest.raises(ValueError, match="nonexistent_edge"):
            build_join(js, COMPONENT_SPECS)

    def test_malformed_edge_ref_raises(self):
        js = JoinSpec("j1", JoinType.CONTINUATION, "no_dot_here", "body.top")
        with pytest.raises(ValueError, match="no_dot_here"):
            build_join(js, COMPONENT_SPECS)


class TestBuildAllJoins:
    def test_returns_list_of_joins(self):
        specs = (JoinSpec("j1", JoinType.CONTINUATION, "yoke.body_join", "body.top"),)
        result = build_all_joins(specs, COMPONENT_SPECS)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_empty_join_specs(self):
        result = build_all_joins((), COMPONENT_SPECS)
        assert result == []

    def test_multiple_joins(self):
        sleeve_spec = _spec("sleeve", Edge("top", EdgeType.LIVE_STITCH))
        # body.hem is BOUND_OFF but HELD_STITCH requires LIVE_STITCH;
        # use a proper LIVE_STITCH armhole edge for the second join.
        body_with_armhole = _spec(
            "body",
            Edge("top", EdgeType.LIVE_STITCH, join_ref="j1"),
            Edge("hem", EdgeType.BOUND_OFF),
            Edge("armhole", EdgeType.LIVE_STITCH, join_ref="j2"),
        )
        specs2 = {"yoke": YOKE_SPEC, "body": body_with_armhole, "sleeve": sleeve_spec}
        join_specs2 = (
            JoinSpec("j1", JoinType.CONTINUATION, "yoke.body_join", "body.top"),
            JoinSpec("j2", JoinType.HELD_STITCH, "body.armhole", "sleeve.top"),
        )
        result = build_all_joins(join_specs2, specs2)
        assert len(result) == 2
        assert result[0].id == "j1"
        assert result[1].id == "j2"
