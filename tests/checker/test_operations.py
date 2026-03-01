"""Tests for checker.operations — execute_op for each OpType."""

from __future__ import annotations

import pytest

from skyknit.checker.operations import execute_op
from skyknit.checker.vm_state import VMState
from skyknit.schemas.ir import Operation, OpType


def make_op(
    op_type: OpType,
    parameters: dict | None = None,
    row_count: int | None = None,
    stitch_count_after: int | None = None,
) -> Operation:
    return Operation(
        op_type=op_type,
        parameters=parameters or {},
        row_count=row_count,
        stitch_count_after=stitch_count_after,
    )


class TestCastOn:
    def test_sets_live_stitch_count(self):
        state = VMState()
        execute_op(state, make_op(OpType.CAST_ON, {"count": 80}))
        assert state.live_stitch_count == 80

    def test_row_counter_unchanged(self):
        state = VMState()
        execute_op(state, make_op(OpType.CAST_ON, {"count": 80}))
        assert state.row_counter == 0

    def test_rejects_negative_count(self):
        state = VMState()
        with pytest.raises(ValueError, match="CAST_ON count must be >= 0"):
            execute_op(state, make_op(OpType.CAST_ON, {"count": -1}))


class TestWorkEven:
    def test_stitch_count_unchanged(self):
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.WORK_EVEN, row_count=20))
        assert state.live_stitch_count == 80

    def test_row_counter_advances(self):
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.WORK_EVEN, row_count=20))
        assert state.row_counter == 20

    def test_accumulates_rows(self):
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.WORK_EVEN, row_count=10))
        execute_op(state, make_op(OpType.WORK_EVEN, row_count=15))
        assert state.row_counter == 25

    def test_rejects_missing_row_count(self):
        state = VMState(live_stitch_count=80)
        with pytest.raises(ValueError, match="row_count"):
            execute_op(state, make_op(OpType.WORK_EVEN))


class TestIncreaseSection:
    def test_stitch_count_increases(self):
        state = VMState(live_stitch_count=60)
        execute_op(state, make_op(OpType.INCREASE_SECTION, row_count=20, stitch_count_after=80))
        assert state.live_stitch_count == 80

    def test_row_counter_advances(self):
        state = VMState(live_stitch_count=60)
        execute_op(state, make_op(OpType.INCREASE_SECTION, row_count=20, stitch_count_after=80))
        assert state.row_counter == 20

    def test_rejects_decrease_as_increase(self):
        state = VMState(live_stitch_count=80)
        with pytest.raises(ValueError, match="must be >="):
            execute_op(state, make_op(OpType.INCREASE_SECTION, row_count=10, stitch_count_after=60))


class TestDecreaseSection:
    def test_stitch_count_decreases(self):
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.DECREASE_SECTION, row_count=20, stitch_count_after=60))
        assert state.live_stitch_count == 60

    def test_row_counter_advances(self):
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.DECREASE_SECTION, row_count=20, stitch_count_after=60))
        assert state.row_counter == 20

    def test_rejects_increase_as_decrease(self):
        state = VMState(live_stitch_count=60)
        with pytest.raises(ValueError, match="must be <="):
            execute_op(state, make_op(OpType.DECREASE_SECTION, row_count=10, stitch_count_after=80))

    def test_rejects_negative_result(self):
        state = VMState(live_stitch_count=60)
        with pytest.raises(ValueError, match="must be >= 0"):
            execute_op(state, make_op(OpType.DECREASE_SECTION, row_count=10, stitch_count_after=-1))


class TestBindOff:
    def test_live_count_becomes_zero(self):
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.BIND_OFF, {"count": 80}))
        assert state.live_stitch_count == 0

    def test_rejects_count_mismatch(self):
        state = VMState(live_stitch_count=80)
        with pytest.raises(ValueError, match="does not match live stitch count"):
            execute_op(state, make_op(OpType.BIND_OFF, {"count": 60}))

    def test_accepts_omitted_count(self):
        """BIND_OFF without explicit count is valid — binds off whatever is live."""
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.BIND_OFF))
        assert state.live_stitch_count == 0


class TestHold:
    def test_live_decreases_held_increases(self):
        state = VMState(live_stitch_count=80)
        execute_op(state, make_op(OpType.HOLD, {"count": 12, "label": "underarm"}))
        assert state.live_stitch_count == 68
        assert state.held_stitches["underarm"] == 12

    def test_rejects_hold_more_than_live(self):
        state = VMState(live_stitch_count=10)
        with pytest.raises(ValueError, match="exceeds live stitch count"):
            execute_op(state, make_op(OpType.HOLD, {"count": 20, "label": "x"}))

    def test_multiple_holds(self):
        state = VMState(live_stitch_count=100)
        execute_op(state, make_op(OpType.HOLD, {"count": 12, "label": "left"}))
        execute_op(state, make_op(OpType.HOLD, {"count": 12, "label": "right"}))
        assert state.live_stitch_count == 76
        assert state.held_stitches["left"] == 12
        assert state.held_stitches["right"] == 12


class TestPickupStitches:
    def test_live_count_increases(self):
        state = VMState(live_stitch_count=0)
        execute_op(state, make_op(OpType.PICKUP_STITCHES, {"count": 48}))
        assert state.live_stitch_count == 48

    def test_rejects_negative_count(self):
        state = VMState(live_stitch_count=80)
        with pytest.raises(ValueError, match="PICKUP_STITCHES count must be >= 0"):
            execute_op(state, make_op(OpType.PICKUP_STITCHES, {"count": -5}))


class TestReturnValue:
    def test_returns_same_state_object(self):
        """execute_op returns the mutated state (same object) for chaining."""
        state = VMState()
        result = execute_op(state, make_op(OpType.CAST_ON, {"count": 80}))
        assert result is state
