"""Tests for validator.spatial — validate_spatial_coherence."""

from __future__ import annotations

from schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from topology.types import Edge, EdgeType, Join, JoinType
from validator.spatial import validate_spatial_coherence


def _spec(name: str, edges: tuple) -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": 914.4, "depth_mm": 457.2},
        edges=edges,
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


def _join(join_id: str, edge_a: str, edge_b: str) -> Join:
    return Join(
        id=join_id,
        join_type=JoinType.CONTINUATION,
        edge_a_ref=edge_a,
        edge_b_ref=edge_b,
    )


class TestValidManifest:
    def test_coherent_manifest_passes(self):
        manifest = ShapeManifest(
            components=(
                _spec("yoke", (Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", "yoke.bottom", "body.top"),),
        )
        errors = validate_spatial_coherence(manifest)
        assert errors == []

    def test_empty_manifest_passes(self):
        errors = validate_spatial_coherence(ShapeManifest(components=(), joins=()))
        assert errors == []

    def test_no_joins_no_join_refs_passes(self):
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),)),
            ),
            joins=(),
        )
        errors = validate_spatial_coherence(manifest)
        assert errors == []


class TestDanglingJoinRef:
    def test_edge_join_ref_pointing_to_missing_join(self):
        """An edge's join_ref names a join that isn't in the manifest."""
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="missing_join"),)),
            ),
            joins=(),  # no joins at all
        )
        errors = validate_spatial_coherence(manifest)
        assert len(errors) >= 1
        assert any("missing_join" in e.message for e in errors)
        assert all(e.severity == "error" for e in errors)

    def test_none_join_ref_is_fine(self):
        """join_ref=None means no join — this should not be flagged."""
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),)),
            ),
            joins=(),
        )
        errors = validate_spatial_coherence(manifest)
        assert errors == []


class TestJoinReferencingNonExistentEdge:
    def test_edge_a_ref_not_in_manifest(self):
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", "ghost.bottom", "body.top"),),
        )
        errors = validate_spatial_coherence(manifest)
        assert any("ghost.bottom" in e.message for e in errors)

    def test_edge_b_ref_not_in_manifest(self):
        manifest = ShapeManifest(
            components=(
                _spec("yoke", (Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", "yoke.bottom", "phantom.top"),),
        )
        errors = validate_spatial_coherence(manifest)
        assert any("phantom.top" in e.message for e in errors)

    def test_both_refs_missing_produces_two_errors(self):
        manifest = ShapeManifest(
            components=(),
            joins=(_join("j1", "a.top", "b.bottom"),),
        )
        errors = validate_spatial_coherence(manifest)
        assert len(errors) == 2


class TestSelfJoin:
    def test_join_connecting_edge_to_itself_is_error(self):
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", "body.side", "body.side"),),
        )
        errors = validate_spatial_coherence(manifest)
        assert any("same" in e.message.lower() or "distinct" in e.message.lower() for e in errors)
        assert any(e.severity == "error" for e in errors)


class TestReturnType:
    def test_returns_list(self):
        result = validate_spatial_coherence(ShapeManifest(components=(), joins=()))
        assert isinstance(result, list)
