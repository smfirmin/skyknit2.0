"""Tests for validator.compatibility — validate_edge_join_compatibility."""

from __future__ import annotations

from schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from topology.types import Edge, EdgeType, Join, JoinType
from validator.compatibility import ValidationError, validate_edge_join_compatibility

# ── Fixture helpers ────────────────────────────────────────────────────────────


def _spec(name: str, edges: tuple) -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": 914.4, "depth_mm": 457.2},
        edges=edges,
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


def _join(join_id: str, join_type: JoinType, edge_a: str, edge_b: str) -> Join:
    return Join(
        id=join_id,
        join_type=join_type,
        edge_a_ref=edge_a,
        edge_b_ref=edge_b,
    )


class TestValidCombinations:
    def test_live_stitch_continuation_passes(self):
        """LIVE_STITCH + LIVE_STITCH via CONTINUATION → VALID."""
        manifest = ShapeManifest(
            components=(
                _spec(
                    "yoke", (Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)
                ),
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.CONTINUATION, "yoke.bottom", "body.top"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert errors == []

    def test_bound_off_pickup_passes(self):
        """BOUND_OFF + LIVE_STITCH via PICKUP → VALID."""
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="side", edge_type=EdgeType.BOUND_OFF, join_ref="j1"),)),
                _spec("band", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.PICKUP, "body.side", "band.top"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert errors == []

    def test_bound_off_seam_passes(self):
        """BOUND_OFF + BOUND_OFF via SEAM → VALID."""
        manifest = ShapeManifest(
            components=(
                _spec("left", (Edge(name="side", edge_type=EdgeType.BOUND_OFF, join_ref="j1"),)),
                _spec("right", (Edge(name="side", edge_type=EdgeType.BOUND_OFF, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.SEAM, "left.side", "right.side"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert errors == []

    def test_empty_manifest_passes(self):
        manifest = ShapeManifest(components=(), joins=())
        errors = validate_edge_join_compatibility(manifest)
        assert errors == []

    def test_no_joins_passes(self):
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),)),
            ),
            joins=(),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert errors == []


class TestInvalidCombinations:
    def test_invalid_combination_returns_error(self):
        """CAST_ON + LIVE_STITCH via CONTINUATION is not in the table → INVALID."""
        manifest = ShapeManifest(
            components=(
                _spec("a", (Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref="j1"),)),
                _spec("b", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.CONTINUATION, "a.top", "b.top"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert errors[0].join_id == "j1"

    def test_error_message_contains_edge_types(self):
        manifest = ShapeManifest(
            components=(
                _spec("a", (Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref="j1"),)),
                _spec("b", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.CONTINUATION, "a.top", "b.top"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert "CAST_ON" in errors[0].message or "LIVE_STITCH" in errors[0].message


class TestConditionalCombinations:
    def test_conditional_combination_returns_warning(self):
        """LIVE_STITCH + LIVE_STITCH via SEAM → CONDITIONAL → warning."""
        manifest = ShapeManifest(
            components=(
                _spec("front", (Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
                _spec("back", (Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.SEAM, "front.side", "back.side"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert errors[0].join_id == "j1"

    def test_conditional_message_mentions_condition(self):
        manifest = ShapeManifest(
            components=(
                _spec("front", (Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
                _spec("back", (Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.SEAM, "front.side", "back.side"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert "condition" in errors[0].message.lower() or "deferred" in errors[0].message.lower()


class TestTerminalEdges:
    def test_open_edge_as_source_returns_error(self):
        """OPEN is terminal — it must not be edge_a of any join."""
        manifest = ShapeManifest(
            components=(
                _spec("sleeve", (Edge(name="cuff", edge_type=EdgeType.OPEN, join_ref="j1"),)),
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(_join("j1", JoinType.CONTINUATION, "sleeve.cuff", "body.top"),),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert "terminal" in errors[0].message.lower()


class TestMissingEdges:
    def test_unresolvable_edge_a_ref_returns_error(self):
        manifest = ShapeManifest(
            components=(
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(
                Join(
                    id="j1",
                    join_type=JoinType.CONTINUATION,
                    edge_a_ref="nonexistent.bottom",  # not in manifest
                    edge_b_ref="body.top",
                ),
            ),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert len(errors) == 1
        assert "nonexistent.bottom" in errors[0].message

    def test_unresolvable_edge_b_ref_returns_error(self):
        manifest = ShapeManifest(
            components=(
                _spec(
                    "yoke", (Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)
                ),
            ),
            joins=(
                Join(
                    id="j1",
                    join_type=JoinType.CONTINUATION,
                    edge_a_ref="yoke.bottom",
                    edge_b_ref="ghost.top",  # not in manifest
                ),
            ),
        )
        errors = validate_edge_join_compatibility(manifest)
        assert len(errors) == 1
        assert "ghost.top" in errors[0].message


class TestReturnType:
    def test_returns_list_of_validation_errors(self):
        manifest = ShapeManifest(components=(), joins=())
        result = validate_edge_join_compatibility(manifest)
        assert isinstance(result, list)

    def test_validation_error_is_frozen(self):
        err = ValidationError(join_id="j1", message="test", severity="error")
        import pytest

        with pytest.raises(Exception):
            err.message = "changed"  # type: ignore[misc]
