"""Tests for checker.operations — single-operation execution."""

import pytest

from checker.operations import OperationError, execute_op
from checker.vm_state import VMState
from schemas.ir import Operation, OpType


class TestCastOn:
    def test_sets_live_stitch_count(self):
        state = VMState()
        op = Operation(
            op_type=OpType.CAST_ON,
            parameters={"count": 80},
            row_count=None,
            stitch_count_after=80,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 80

    def test_zero_to_n_stitches(self):
        state = VMState(live_stitch_count=0)
        op = Operation(
            op_type=OpType.CAST_ON,
            parameters={"count": 100},
            row_count=None,
            stitch_count_after=100,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 100

    def test_rejects_zero_count(self):
        state = VMState()
        op = Operation(
            op_type=OpType.CAST_ON,
            parameters={"count": 0},
            row_count=None,
            stitch_count_after=0,
        )
        with pytest.raises(OperationError, match="CAST_ON count must be positive"):
            execute_op(state, op)

    def test_rejects_negative_count(self):
        state = VMState()
        op = Operation(
            op_type=OpType.CAST_ON,
            parameters={"count": -10},
            row_count=None,
            stitch_count_after=-10,
        )
        with pytest.raises(OperationError, match="CAST_ON count must be positive"):
            execute_op(state, op)


class TestWorkEven:
    def test_stitch_count_unchanged(self):
        state = VMState(live_stitch_count=80)
        op = Operation(
            op_type=OpType.WORK_EVEN,
            parameters={},
            row_count=20,
            stitch_count_after=80,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 80

    def test_rows_advance(self):
        state = VMState(live_stitch_count=80, row_counter=0)
        op = Operation(
            op_type=OpType.WORK_EVEN,
            parameters={},
            row_count=20,
            stitch_count_after=80,
        )
        result = execute_op(state, op)
        assert result.row_counter == 20

    def test_rows_accumulate(self):
        state = VMState(live_stitch_count=80, row_counter=10)
        op = Operation(
            op_type=OpType.WORK_EVEN,
            parameters={},
            row_count=20,
            stitch_count_after=80,
        )
        result = execute_op(state, op)
        assert result.row_counter == 30


class TestIncreaseSection:
    def test_stitch_count_increases(self):
        state = VMState(live_stitch_count=80)
        op = Operation(
            op_type=OpType.INCREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=100,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 100

    def test_rows_advance(self):
        state = VMState(live_stitch_count=80, row_counter=5)
        op = Operation(
            op_type=OpType.INCREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=100,
        )
        result = execute_op(state, op)
        assert result.row_counter == 15

    def test_rejects_non_increase(self):
        state = VMState(live_stitch_count=80)
        op = Operation(
            op_type=OpType.INCREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=60,
        )
        with pytest.raises(OperationError, match="must increase stitches"):
            execute_op(state, op)


class TestDecreaseSection:
    def test_stitch_count_decreases(self):
        state = VMState(live_stitch_count=100)
        op = Operation(
            op_type=OpType.DECREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=80,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 80

    def test_rows_advance(self):
        state = VMState(live_stitch_count=100, row_counter=5)
        op = Operation(
            op_type=OpType.DECREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=80,
        )
        result = execute_op(state, op)
        assert result.row_counter == 15

    def test_rejects_non_decrease(self):
        state = VMState(live_stitch_count=80)
        op = Operation(
            op_type=OpType.DECREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=100,
        )
        with pytest.raises(OperationError, match="must decrease stitches"):
            execute_op(state, op)

    def test_rejects_negative_result(self):
        state = VMState(live_stitch_count=10)
        op = Operation(
            op_type=OpType.DECREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=-5,
        )
        with pytest.raises(OperationError, match="negative stitches"):
            execute_op(state, op)


class TestBindOff:
    def test_stitch_count_to_zero(self):
        state = VMState(live_stitch_count=80)
        op = Operation(
            op_type=OpType.BIND_OFF,
            parameters={"count": 80},
            row_count=None,
            stitch_count_after=0,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 0

    def test_partial_bind_off(self):
        state = VMState(live_stitch_count=80)
        op = Operation(
            op_type=OpType.BIND_OFF,
            parameters={"count": 30},
            row_count=None,
            stitch_count_after=50,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 50

    def test_rejects_excess_bind_off(self):
        state = VMState(live_stitch_count=40)
        op = Operation(
            op_type=OpType.BIND_OFF,
            parameters={"count": 80},
            row_count=None,
            stitch_count_after=0,
        )
        with pytest.raises(OperationError, match="exceeds live stitches"):
            execute_op(state, op)


class TestHold:
    def test_live_decreases_held_increases(self):
        state = VMState(live_stitch_count=80)
        op = Operation(
            op_type=OpType.HOLD,
            parameters={"label": "sleeve", "count": 20},
            row_count=None,
            stitch_count_after=60,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 60
        assert result.held_stitches["sleeve"] == 20

    def test_hold_accumulates(self):
        state = VMState(live_stitch_count=80, held_stitches={"sleeve": 10})
        op = Operation(
            op_type=OpType.HOLD,
            parameters={"label": "sleeve", "count": 20},
            row_count=None,
            stitch_count_after=60,
        )
        result = execute_op(state, op)
        assert result.held_stitches["sleeve"] == 30

    def test_rejects_excess_hold(self):
        state = VMState(live_stitch_count=10)
        op = Operation(
            op_type=OpType.HOLD,
            parameters={"label": "sleeve", "count": 20},
            row_count=None,
            stitch_count_after=None,
        )
        with pytest.raises(OperationError, match="exceeds live stitches"):
            execute_op(state, op)


class TestSeparate:
    def test_splits_into_groups(self):
        state = VMState(live_stitch_count=100)
        op = Operation(
            op_type=OpType.SEPARATE,
            parameters={
                "groups": {"front": 40, "left_sleeve": 30, "right_sleeve": 30},
                "active_group": "front",
            },
            row_count=None,
            stitch_count_after=40,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 40
        assert result.held_stitches["left_sleeve"] == 30
        assert result.held_stitches["right_sleeve"] == 30

    def test_rejects_mismatched_total(self):
        state = VMState(live_stitch_count=100)
        op = Operation(
            op_type=OpType.SEPARATE,
            parameters={
                "groups": {"front": 40, "back": 40},
                "active_group": "front",
            },
            row_count=None,
            stitch_count_after=40,
        )
        with pytest.raises(OperationError, match="does not match"):
            execute_op(state, op)


class TestPickupStitches:
    def test_adds_stitches(self):
        state = VMState(live_stitch_count=0)
        op = Operation(
            op_type=OpType.PICKUP_STITCHES,
            parameters={"count": 60},
            row_count=None,
            stitch_count_after=60,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 60

    def test_pickup_from_held(self):
        state = VMState(live_stitch_count=0, held_stitches={"sleeve": 40})
        op = Operation(
            op_type=OpType.PICKUP_STITCHES,
            parameters={"count": 40, "source": "sleeve"},
            row_count=None,
            stitch_count_after=40,
        )
        result = execute_op(state, op)
        assert result.live_stitch_count == 40
        assert "sleeve" not in result.held_stitches

    def test_rejects_excess_pickup_from_held(self):
        state = VMState(live_stitch_count=0, held_stitches={"sleeve": 20})
        op = Operation(
            op_type=OpType.PICKUP_STITCHES,
            parameters={"count": 40, "source": "sleeve"},
            row_count=None,
            stitch_count_after=40,
        )
        with pytest.raises(OperationError, match="exceeds held stitches"):
            execute_op(state, op)


class TestInvalidOperation:
    def test_rejects_negative_stitches_via_decrease(self):
        state = VMState(live_stitch_count=5)
        op = Operation(
            op_type=OpType.DECREASE_SECTION,
            parameters={},
            row_count=10,
            stitch_count_after=-5,
        )
        with pytest.raises(OperationError):
            execute_op(state, op)
