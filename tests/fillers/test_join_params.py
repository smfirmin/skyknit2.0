"""Tests for fillers.join_params — read_join_parameters."""

from __future__ import annotations

from types import MappingProxyType

from skyknit.fillers.join_params import read_join_parameters
from skyknit.topology.types import Join, JoinType


def _join(join_type: JoinType, params: dict | None = None) -> Join:
    return Join(
        id="test_join",
        join_type=join_type,
        edge_a_ref="a.top",
        edge_b_ref="b.bottom",
        parameters=MappingProxyType(params or {}),
    )


class TestCastOnJoin:
    def test_returns_cast_on_count(self):
        join = _join(JoinType.CAST_ON_JOIN, {"cast_on_count": 8, "cast_on_method": "long-tail"})
        params = read_join_parameters(join, "a.top")
        assert params["cast_on_count"] == 8

    def test_returns_cast_on_method(self):
        join = _join(JoinType.CAST_ON_JOIN, {"cast_on_count": 8, "cast_on_method": "long-tail"})
        params = read_join_parameters(join, "a.top")
        assert params["cast_on_method"] == "long-tail"

    def test_missing_optional_key_not_included(self):
        """cast_on_method is optional — absent keys are silently skipped."""
        join = _join(JoinType.CAST_ON_JOIN, {"cast_on_count": 8})
        params = read_join_parameters(join, "a.top")
        assert "cast_on_method" not in params
        assert params["cast_on_count"] == 8


class TestPickup:
    def test_returns_pickup_ratio(self):
        join = _join(JoinType.PICKUP, {"pickup_ratio": 0.75, "pickup_direction": "right_to_left"})
        params = read_join_parameters(join, "a.top")
        assert params["pickup_ratio"] == 0.75

    def test_returns_pickup_direction(self):
        join = _join(JoinType.PICKUP, {"pickup_ratio": 0.75, "pickup_direction": "right_to_left"})
        params = read_join_parameters(join, "b.bottom")
        assert params["pickup_direction"] == "right_to_left"


class TestContinuation:
    def test_returns_empty_dict(self):
        join = _join(JoinType.CONTINUATION)
        params = read_join_parameters(join, "a.top")
        assert params == {}


class TestHeldStitch:
    def test_returns_empty_dict(self):
        join = _join(JoinType.HELD_STITCH)
        params = read_join_parameters(join, "a.top")
        assert params == {}


class TestSeam:
    def test_returns_seam_method(self):
        join = _join(JoinType.SEAM, {"seam_method": "mattress"})
        params = read_join_parameters(join, "a.top")
        assert params["seam_method"] == "mattress"


class TestImmutability:
    def test_returned_dict_is_a_copy(self):
        """Mutating the returned dict must not affect the Join."""
        join = _join(JoinType.CAST_ON_JOIN, {"cast_on_count": 8})
        params = read_join_parameters(join, "a.top")
        params["cast_on_count"] = 999
        assert join.parameters["cast_on_count"] == 8

    def test_returned_dict_is_mutable(self):
        join = _join(JoinType.PICKUP, {"pickup_ratio": 0.75})
        params = read_join_parameters(join, "a.top")
        params["new_key"] = "added"  # should not raise
        assert "new_key" in params
