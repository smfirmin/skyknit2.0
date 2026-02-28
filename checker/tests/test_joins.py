"""Tests for checker.joins — validate_join and validate_all_joins."""

from __future__ import annotations

from types import MappingProxyType

from checker.joins import validate_all_joins, validate_join
from checker.simulate import CheckerError
from topology.types import Join, JoinType
from utilities.types import Gauge

# Gauge: 20 sts/inch, 28 rows/inch → 1 stitch ≈ 1.27mm
GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
TOLERANCE_MM = 10.0  # generous for testing


def _join(join_type: JoinType, edge_a: str, edge_b: str, params: dict | None = None) -> Join:
    return Join(
        id=f"{edge_a}_to_{edge_b}",
        join_type=join_type,
        edge_a_ref=edge_a,
        edge_b_ref=edge_b,
        parameters=MappingProxyType(params or {}),
    )


class TestOneToOne:
    def test_matching_counts_passes(self):
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"yoke.bottom": 80, "body.top": 80}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is None

    def test_mismatched_counts_returns_error(self):
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"yoke.bottom": 80, "body.top": 60}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert isinstance(result, CheckerError)
        assert "ONE_TO_ONE" in result.message

    def test_within_tolerance_passes(self):
        """A 2-stitch difference at 20 sts/inch ≈ 2.54mm, well within 10mm."""
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"yoke.bottom": 80, "body.top": 78}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is None

    def test_outside_tolerance_returns_error(self):
        """A 10-stitch difference at 20 sts/inch = 12.7mm > 10mm."""
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"yoke.bottom": 80, "body.top": 70}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None

    def test_held_stitch_join_one_to_one(self):
        join = _join(JoinType.HELD_STITCH, "body.underarm", "sleeve.underarm")
        counts = {"body.underarm": 12, "sleeve.underarm": 12}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is None

    def test_error_references_join_id(self):
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"yoke.bottom": 80, "body.top": 40}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert join.id in result.message

    def test_error_type_is_geometric(self):
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"yoke.bottom": 80, "body.top": 40}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert result.error_type == "geometric_origin"


class TestAdditive:
    def test_correct_additive_count_passes(self):
        """edge_b = edge_a + cast_on_count."""
        join = _join(JoinType.CAST_ON_JOIN, "body.side", "band.top", {"cast_on_count": 8})
        counts = {"body.side": 80, "band.top": 88}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is None

    def test_wrong_additive_count_returns_error(self):
        join = _join(JoinType.CAST_ON_JOIN, "body.side", "band.top", {"cast_on_count": 8})
        counts = {"body.side": 80, "band.top": 80}  # missing the 8 extra
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert "ADDITIVE" in result.message


class TestRatio:
    def test_correct_ratio_count_passes(self):
        """edge_b = floor(edge_a × pickup_ratio), within tolerance."""
        join = _join(JoinType.PICKUP, "body.selvedge", "band.cast_on", {"pickup_ratio": 0.75})
        counts = {"body.selvedge": 100, "band.cast_on": 75}  # 100 × 0.75 = 75
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is None

    def test_wrong_ratio_count_returns_error(self):
        """50 stitches instead of 75 → difference too large."""
        join = _join(JoinType.PICKUP, "body.selvedge", "band.cast_on", {"pickup_ratio": 0.75})
        counts = {"body.selvedge": 100, "band.cast_on": 50}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert "RATIO" in result.message


class TestStructural:
    def test_matching_seam_counts_passes(self):
        join = _join(JoinType.SEAM, "left_front.side", "right_front.side")
        counts = {"left_front.side": 60, "right_front.side": 60}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is None

    def test_mismatched_seam_returns_error(self):
        join = _join(JoinType.SEAM, "left_front.side", "right_front.side")
        counts = {"left_front.side": 60, "right_front.side": 30}
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert "STRUCTURAL" in result.message


class TestMissingEdges:
    def test_missing_edge_a_returns_error(self):
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"body.top": 80}  # edge_a missing
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert "yoke.bottom" in result.message

    def test_missing_edge_b_returns_error(self):
        join = _join(JoinType.CONTINUATION, "yoke.bottom", "body.top")
        counts = {"yoke.bottom": 80}  # edge_b missing
        result = validate_join(join, counts, TOLERANCE_MM, GAUGE)
        assert result is not None
        assert "body.top" in result.message


class TestValidateAllJoins:
    def test_no_errors_when_all_valid(self):
        joins = [
            _join(JoinType.CONTINUATION, "yoke.bottom", "body.top"),
            _join(JoinType.CONTINUATION, "yoke.sleeve", "sleeve.top"),
        ]
        counts = {
            "yoke.bottom": 80,
            "body.top": 80,
            "yoke.sleeve": 60,
            "sleeve.top": 60,
        }
        errors = validate_all_joins(joins, counts, TOLERANCE_MM, GAUGE)
        assert errors == []

    def test_collects_all_errors(self):
        joins = [
            _join(JoinType.CONTINUATION, "yoke.bottom", "body.top"),
            _join(JoinType.CONTINUATION, "yoke.sleeve", "sleeve.top"),
        ]
        counts = {
            "yoke.bottom": 80,
            "body.top": 40,  # mismatch
            "yoke.sleeve": 60,
            "sleeve.top": 20,  # mismatch
        }
        errors = validate_all_joins(joins, counts, TOLERANCE_MM, GAUGE)
        assert len(errors) == 2

    def test_returns_list(self):
        errors = validate_all_joins([], {}, TOLERANCE_MM, GAUGE)
        assert isinstance(errors, list)
        assert errors == []
