"""Tests for schemas.manifest — ShapeManifest, ComponentSpec, ShapeType, Handedness."""

import pytest

from schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from topology.types import Edge, EdgeType, Join, JoinType


@pytest.fixture(scope="module")
def body_component():
    top_edge = Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="join_body_yoke")
    bottom_edge = Edge(name="bottom", edge_type=EdgeType.OPEN)
    return ComponentSpec(
        name="body",
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": 1016.0, "depth_mm": 431.8},
        edges=(top_edge, bottom_edge),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


@pytest.fixture(scope="module")
def sleeve_component():
    cap_edge = Edge(name="cap", edge_type=EdgeType.LIVE_STITCH, join_ref="join_sleeve_yoke")
    cuff_edge = Edge(name="cuff", edge_type=EdgeType.OPEN)
    return ComponentSpec(
        name="sleeve",
        shape_type=ShapeType.TRAPEZOID,
        dimensions={
            "circumference_top_mm": 431.8,
            "circumference_bottom_mm": 228.6,
            "depth_mm": 457.2,
        },
        edges=(cap_edge, cuff_edge),
        handedness=Handedness.LEFT,
        instantiation_count=2,
    )


class TestShapeType:
    def test_members(self):
        assert ShapeType.CYLINDER.value == "CYLINDER"
        assert ShapeType.TRAPEZOID.value == "TRAPEZOID"
        assert ShapeType.RECTANGLE.value == "RECTANGLE"

    def test_is_str_enum(self):
        assert isinstance(ShapeType.CYLINDER, str)


class TestHandedness:
    def test_members(self):
        assert Handedness.LEFT.value == "LEFT"
        assert Handedness.RIGHT.value == "RIGHT"
        assert Handedness.NONE.value == "NONE"


class TestComponentSpec:
    def test_construction(self, body_component):
        assert body_component.name == "body"
        assert body_component.shape_type is ShapeType.CYLINDER
        assert body_component.dimensions["circumference_mm"] == pytest.approx(1016.0)
        assert len(body_component.edges) == 2
        assert body_component.handedness is Handedness.NONE
        assert body_component.instantiation_count == 1

    def test_is_frozen(self, body_component):
        with pytest.raises(AttributeError):
            body_component.name = "torso"

    def test_edges_reference_topology_edge_type(self, body_component):
        """Edge types come from topology.EdgeType — not a redefined schema enum."""
        for edge in body_component.edges:
            assert isinstance(edge.edge_type, EdgeType)

    def test_symmetric_component_instantiation_count(self, sleeve_component):
        assert sleeve_component.instantiation_count == 2

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            ComponentSpec(
                name="",
                shape_type=ShapeType.RECTANGLE,
                dimensions={"width_mm": 100.0},
                edges=(),
                handedness=Handedness.NONE,
                instantiation_count=1,
            )

    def test_rejects_zero_instantiation_count(self):
        with pytest.raises(ValueError, match="instantiation_count must be >= 1"):
            ComponentSpec(
                name="cuff",
                shape_type=ShapeType.RECTANGLE,
                dimensions={"width_mm": 100.0},
                edges=(),
                handedness=Handedness.NONE,
                instantiation_count=0,
            )

    def test_rejects_duplicate_edge_names(self):
        e1 = Edge(name="top", edge_type=EdgeType.LIVE_STITCH)
        e2 = Edge(name="top", edge_type=EdgeType.OPEN)
        with pytest.raises(ValueError, match="edge names must be unique"):
            ComponentSpec(
                name="bad_component",
                shape_type=ShapeType.RECTANGLE,
                dimensions={},
                edges=(e1, e2),
                handedness=Handedness.NONE,
                instantiation_count=1,
            )


class TestShapeManifest:
    def test_construction(self, body_component, sleeve_component):
        join = Join(
            id="join_sleeve_yoke",
            join_type=JoinType.HELD_STITCH,
            edge_a_ref="yoke.left_underarm",
            edge_b_ref="sleeve.cap",
        )
        manifest = ShapeManifest(
            components=(body_component, sleeve_component),
            joins=(join,),
        )
        assert len(manifest.components) == 2
        assert len(manifest.joins) == 1

    def test_is_frozen(self, body_component):
        manifest = ShapeManifest(components=(body_component,), joins=())
        with pytest.raises(AttributeError):
            manifest.components = ()  # type: ignore[misc]

    def test_joins_reference_topology_join_type(self, body_component):
        """Join types come from topology.JoinType — not a redefined schema enum."""
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="yoke.bottom",
            edge_b_ref="body.top",
        )
        manifest = ShapeManifest(components=(body_component,), joins=(join,))
        for j in manifest.joins:
            assert isinstance(j.join_type, JoinType)

    def test_join_edge_refs_use_dot_notation(self, body_component):
        """Join edge refs are 'component_name.edge_name' strings."""
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="yoke.bottom",
            edge_b_ref="body.top",
        )
        manifest = ShapeManifest(components=(body_component,), joins=(join,))
        j = manifest.joins[0]
        assert "." in j.edge_a_ref
        assert "." in j.edge_b_ref

    def test_empty_manifest_allowed(self):
        manifest = ShapeManifest(components=(), joins=())
        assert manifest.components == ()
        assert manifest.joins == ()
