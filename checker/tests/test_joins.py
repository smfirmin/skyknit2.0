"""Tests for checker.joins — inter-component join validation."""

import pytest

from checker.joins import validate_all_joins, validate_join
from topology.types import Join, JoinType
from utilities.types import Gauge


@pytest.fixture
def gauge():
    return Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)


class TestOneToOne:
    def test_matching_counts_pass(self, gauge):
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="body.bottom",
            edge_b_ref="skirt.top",
        )
        edge_counts = {"body.bottom": 100, "skirt.top": 100}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is None

    def test_mismatched_counts_fail(self, gauge):
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="body.bottom",
            edge_b_ref="skirt.top",
        )
        edge_counts = {"body.bottom": 100, "skirt.top": 80}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is not None
        assert "ONE_TO_ONE" in result.message

    def test_within_tolerance_passes(self, gauge):
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="body.bottom",
            edge_b_ref="skirt.top",
        )
        # tolerance_mm=5.08 at 5 sts/inch = 1 stitch tolerance
        edge_counts = {"body.bottom": 100, "skirt.top": 101}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is None


class TestAdditive:
    def test_correct_cast_on_count_pass(self, gauge):
        join = Join(
            id="j2",
            join_type=JoinType.CAST_ON_JOIN,
            edge_a_ref="yoke.bottom",
            edge_b_ref="body.top",
            parameters={"cast_on_count": 10, "cast_on_method": "long_tail"},
        )
        edge_counts = {"yoke.bottom": 100, "body.top": 110}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is None

    def test_wrong_count_fails(self, gauge):
        join = Join(
            id="j2",
            join_type=JoinType.CAST_ON_JOIN,
            edge_a_ref="yoke.bottom",
            edge_b_ref="body.top",
            parameters={"cast_on_count": 10, "cast_on_method": "long_tail"},
        )
        edge_counts = {"yoke.bottom": 100, "body.top": 130}  # expected 110
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is not None
        assert "ADDITIVE" in result.message


class TestRatio:
    def test_correct_ratio_pass(self, gauge):
        join = Join(
            id="j3",
            join_type=JoinType.PICKUP,
            edge_a_ref="body.selvedge",
            edge_b_ref="collar.bottom",
            parameters={"pickup_ratio": 0.75, "pickup_direction": "bottom_up"},
        )
        edge_counts = {"body.selvedge": 100, "collar.bottom": 75}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is None

    def test_wrong_ratio_fails(self, gauge):
        join = Join(
            id="j3",
            join_type=JoinType.PICKUP,
            edge_a_ref="body.selvedge",
            edge_b_ref="collar.bottom",
            parameters={"pickup_ratio": 0.75, "pickup_direction": "bottom_up"},
        )
        edge_counts = {"body.selvedge": 100, "collar.bottom": 50}  # expected 75
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is not None
        assert "RATIO" in result.message


class TestStructural:
    def test_matching_counts_pass(self, gauge):
        join = Join(
            id="j4",
            join_type=JoinType.SEAM,
            edge_a_ref="front.side",
            edge_b_ref="back.side",
            parameters={"seam_method": "mattress"},
        )
        edge_counts = {"front.side": 80, "back.side": 80}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is None

    def test_mismatched_counts_fail(self, gauge):
        join = Join(
            id="j4",
            join_type=JoinType.SEAM,
            edge_a_ref="front.side",
            edge_b_ref="back.side",
            parameters={"seam_method": "mattress"},
        )
        edge_counts = {"front.side": 80, "back.side": 60}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is not None
        assert "STRUCTURAL" in result.message


class TestHeldStitch:
    """HELD_STITCH uses ONE_TO_ONE arithmetic — same as CONTINUATION."""

    def test_matching_counts_pass(self, gauge):
        join = Join(
            id="j5",
            join_type=JoinType.HELD_STITCH,
            edge_a_ref="yoke.sleeve_hold",
            edge_b_ref="sleeve.top",
        )
        edge_counts = {"yoke.sleeve_hold": 40, "sleeve.top": 40}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is None

    def test_mismatched_counts_fail(self, gauge):
        join = Join(
            id="j5",
            join_type=JoinType.HELD_STITCH,
            edge_a_ref="yoke.sleeve_hold",
            edge_b_ref="sleeve.top",
        )
        edge_counts = {"yoke.sleeve_hold": 40, "sleeve.top": 60}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is not None
        assert "ONE_TO_ONE" in result.message


class TestMissingEdgeCounts:
    def test_missing_edge_a(self, gauge):
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="body.bottom",
            edge_b_ref="skirt.top",
        )
        edge_counts = {"skirt.top": 100}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is not None
        assert "Missing edge count" in result.message

    def test_missing_edge_b(self, gauge):
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="body.bottom",
            edge_b_ref="skirt.top",
        )
        edge_counts = {"body.bottom": 100}
        result = validate_join(join, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert result is not None
        assert "Missing edge count" in result.message


class TestValidateAllJoins:
    def test_all_valid_returns_empty(self, gauge):
        joins = (
            Join(
                id="j1",
                join_type=JoinType.CONTINUATION,
                edge_a_ref="body.bottom",
                edge_b_ref="skirt.top",
            ),
        )
        edge_counts = {"body.bottom": 100, "skirt.top": 100}
        errors = validate_all_joins(joins, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert errors == []

    def test_mixed_valid_invalid(self, gauge):
        joins = (
            Join(
                id="j1",
                join_type=JoinType.CONTINUATION,
                edge_a_ref="body.bottom",
                edge_b_ref="skirt.top",
            ),
            Join(
                id="j2",
                join_type=JoinType.SEAM,
                edge_a_ref="front.side",
                edge_b_ref="back.side",
                parameters={"seam_method": "mattress"},
            ),
        )
        edge_counts = {
            "body.bottom": 100,
            "skirt.top": 100,
            "front.side": 80,
            "back.side": 60,  # mismatch
        }
        errors = validate_all_joins(joins, edge_counts, tolerance_mm=5.08, gauge=gauge)
        assert len(errors) == 1
        assert "j2" in errors[0].message
