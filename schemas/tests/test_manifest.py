"""Tests for schemas.manifest — ShapeManifest, ComponentSpec, ShapeType, Handedness."""

import pytest

from schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from topology.types import Edge, EdgeType, Join, JoinType


@pytest.fixture
def body_edges():
    return (
        Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_body_join"),
        Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
    )


@pytest.fixture
def body_spec(body_edges):
    return ComponentSpec(
        name="body",
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": 914.4, "depth_mm": 457.2},
        edges=body_edges,
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


@pytest.fixture
def sleeve_spec():
    return ComponentSpec(
        name="sleeve",
        shape_type=ShapeType.TRAPEZOID,
        dimensions={
            "top_circumference_mm": 457.2,
            "bottom_circumference_mm": 304.8,
            "depth_mm": 457.2,
        },
        edges=(
            Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_sleeve_join"),
            Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
        ),
        handedness=Handedness.LEFT,
        instantiation_count=2,
    )


@pytest.fixture
def sample_join():
    return Join(
        id="yoke_body_join",
        join_type=JoinType.CONTINUATION,
        edge_a_ref="yoke.bottom",
        edge_b_ref="body.top",
    )


@pytest.fixture
def sample_manifest(body_spec, sleeve_spec, sample_join):
    return ShapeManifest(
        components=(body_spec, sleeve_spec),
        joins=(sample_join,),
    )


class TestShapeType:
    def test_members_exist(self):
        assert ShapeType.CYLINDER
        assert ShapeType.TRAPEZOID
        assert ShapeType.RECTANGLE

    def test_is_string_enum(self):
        assert isinstance(ShapeType.CYLINDER, str)


class TestHandedness:
    def test_members_exist(self):
        assert Handedness.LEFT
        assert Handedness.RIGHT
        assert Handedness.NONE

    def test_is_string_enum(self):
        assert isinstance(Handedness.LEFT, str)


class TestComponentSpec:
    def test_construction(self, body_spec, body_edges):
        assert body_spec.name == "body"
        assert body_spec.shape_type == ShapeType.CYLINDER
        assert body_spec.handedness == Handedness.NONE
        assert body_spec.instantiation_count == 1
        assert body_spec.edges == body_edges

    def test_is_frozen(self, body_spec):
        with pytest.raises(Exception):
            body_spec.name = "torso"

    def test_edges_reference_topology_edge_type(self, body_spec):
        """Edge types must come from topology.EdgeType — not a local enum."""
        for edge in body_spec.edges:
            assert isinstance(edge.edge_type, EdgeType)

    def test_dimensions_are_physical_mm(self, body_spec):
        """Dimensions dict values are floats (mm)."""
        for v in body_spec.dimensions.values():
            assert isinstance(v, float)

    def test_dimensions_are_immutable(self, body_spec):
        from types import MappingProxyType

        assert isinstance(body_spec.dimensions, MappingProxyType)
        with pytest.raises(TypeError):
            body_spec.dimensions["new_key"] = 1.0  # type: ignore[index]

    def test_instantiation_count(self, sleeve_spec):
        assert sleeve_spec.instantiation_count == 2

    def test_rejects_zero_instantiation_count(self, body_edges):
        with pytest.raises(ValueError, match="instantiation_count must be >= 1"):
            ComponentSpec(
                name="ghost",
                shape_type=ShapeType.RECTANGLE,
                dimensions={"width_mm": 100.0},
                edges=body_edges,
                handedness=Handedness.NONE,
                instantiation_count=0,
            )

    def test_plain_dict_dimensions_auto_converted(self, body_edges):
        """Plain dict passed for dimensions is promoted to MappingProxyType."""
        from types import MappingProxyType

        spec = ComponentSpec(
            name="test",
            shape_type=ShapeType.RECTANGLE,
            dimensions={"width_mm": 200.0},
            edges=body_edges,
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        assert isinstance(spec.dimensions, MappingProxyType)


class TestShapeManifest:
    def test_construction(self, sample_manifest, body_spec, sleeve_spec, sample_join):
        assert len(sample_manifest.components) == 2
        assert sample_manifest.components[0] == body_spec
        assert sample_manifest.components[1] == sleeve_spec
        assert len(sample_manifest.joins) == 1
        assert sample_manifest.joins[0] == sample_join

    def test_is_frozen(self, sample_manifest):
        with pytest.raises(Exception):
            sample_manifest.components = ()

    def test_joins_reference_topology_join_type(self, sample_manifest):
        """Join types must come from topology.JoinType."""
        for join in sample_manifest.joins:
            assert isinstance(join.join_type, JoinType)

    def test_joins_use_component_dot_edge_format(self, sample_join):
        """edge_a_ref and edge_b_ref follow 'component.edge' naming convention."""
        assert "." in sample_join.edge_a_ref
        assert "." in sample_join.edge_b_ref

    def test_components_edges_referenced_by_name(self, body_spec):
        edge_names = [e.name for e in body_spec.edges]
        assert "top" in edge_names
        assert "bottom" in edge_names
