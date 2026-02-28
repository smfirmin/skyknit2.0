"""Tests for validator.phase1 — validate_phase1 and ValidationResult."""

from __future__ import annotations

import pytest

from schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from topology.types import Edge, EdgeType, Join, JoinType
from validator.compatibility import ValidationError
from validator.phase1 import ValidationResult, validate_phase1


def _spec(name: str, edges: tuple) -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": 914.4, "depth_mm": 457.2},
        edges=edges,
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


class TestValidationResult:
    def test_is_frozen(self):
        result = ValidationResult(passed=True, errors=())
        with pytest.raises(Exception):
            result.passed = False  # type: ignore[misc]

    def test_warnings_do_not_fail(self):
        """A result with only warnings should still pass."""
        warning = ValidationError(join_id="j1", message="conditional", severity="warning")
        result = ValidationResult(passed=True, errors=(warning,))
        assert result.passed is True


class TestValidManifest:
    def test_valid_manifest_passes(self):
        """LIVE_STITCH → LIVE_STITCH via CONTINUATION with correct refs → pass."""
        manifest = ShapeManifest(
            components=(
                _spec(
                    "yoke", (Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)
                ),
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(
                Join(
                    id="j1",
                    join_type=JoinType.CONTINUATION,
                    edge_a_ref="yoke.bottom",
                    edge_b_ref="body.top",
                ),
            ),
        )
        result = validate_phase1(manifest)
        assert result.passed is True
        assert result.errors == ()

    def test_empty_manifest_passes(self):
        result = validate_phase1(ShapeManifest(components=(), joins=()))
        assert result.passed is True

    def test_returns_validation_result_type(self):
        result = validate_phase1(ShapeManifest(components=(), joins=()))
        assert isinstance(result, ValidationResult)


class TestCompatibilityErrors:
    def test_invalid_edge_join_combination_fails(self):
        """CAST_ON + LIVE_STITCH via CONTINUATION → INVALID → error."""
        manifest = ShapeManifest(
            components=(
                _spec("a", (Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref="j1"),)),
                _spec("b", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(
                Join(
                    id="j1", join_type=JoinType.CONTINUATION, edge_a_ref="a.top", edge_b_ref="b.top"
                ),
            ),
        )
        result = validate_phase1(manifest)
        assert result.passed is False
        assert any(e.severity == "error" for e in result.errors)

    def test_terminal_edge_as_source_fails(self):
        manifest = ShapeManifest(
            components=(
                _spec("sleeve", (Edge(name="cuff", edge_type=EdgeType.OPEN, join_ref="j1"),)),
                _spec("body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(
                Join(
                    id="j1",
                    join_type=JoinType.CONTINUATION,
                    edge_a_ref="sleeve.cuff",
                    edge_b_ref="body.top",
                ),
            ),
        )
        result = validate_phase1(manifest)
        assert result.passed is False


class TestSpatialErrors:
    def test_dangling_join_ref_fails(self):
        manifest = ShapeManifest(
            components=(
                _spec(
                    "body", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="missing"),)
                ),
            ),
            joins=(),
        )
        result = validate_phase1(manifest)
        assert result.passed is False
        assert any("missing" in e.message for e in result.errors)

    def test_join_with_bad_edge_ref_fails(self):
        manifest = ShapeManifest(
            components=(),
            joins=(
                Join(
                    id="j1", join_type=JoinType.CONTINUATION, edge_a_ref="a.top", edge_b_ref="b.top"
                ),
            ),
        )
        result = validate_phase1(manifest)
        assert result.passed is False


class TestCombinedErrors:
    def test_errors_from_both_checks_collected(self):
        """Compatibility error + spatial error both appear in result."""
        # CAST_ON + LIVE_STITCH via CONTINUATION → compat error
        # Plus a dangling join_ref on a separate edge → spatial error
        manifest = ShapeManifest(
            components=(
                _spec(
                    "a",
                    (
                        Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref="j1"),
                        Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="nonexistent"),
                    ),
                ),
                _spec("b", (Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(
                Join(
                    id="j1", join_type=JoinType.CONTINUATION, edge_a_ref="a.top", edge_b_ref="b.top"
                ),
            ),
        )
        result = validate_phase1(manifest)
        assert result.passed is False
        assert len(result.errors) >= 2

    def test_warnings_alone_do_not_fail(self):
        """CONDITIONAL combination → warning only → passed=True."""
        manifest = ShapeManifest(
            components=(
                _spec("front", (Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
                _spec("back", (Edge(name="side", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),)),
            ),
            joins=(
                Join(
                    id="j1",
                    join_type=JoinType.SEAM,
                    edge_a_ref="front.side",
                    edge_b_ref="back.side",
                ),
            ),
        )
        result = validate_phase1(manifest)
        assert result.passed is True
        assert len(result.errors) == 1
        assert result.errors[0].severity == "warning"
