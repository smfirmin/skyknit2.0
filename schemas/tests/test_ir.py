"""Tests for schemas.ir — OpType, Operation, ComponentIR."""

import pytest

from schemas.ir import (
    ComponentIR,
    Operation,
    OpType,
    make_bind_off,
    make_cast_on,
    make_work_even,
)
from schemas.manifest import Handedness


class TestOpType:
    def test_all_members_exist(self):
        expected = {
            "CAST_ON",
            "INCREASE_SECTION",
            "WORK_EVEN",
            "DECREASE_SECTION",
            "SEPARATE",
            "TAPER",
            "BIND_OFF",
            "HOLD",
            "PICKUP_STITCHES",
        }
        assert {m.name for m in OpType} == expected

    def test_is_string_enum(self):
        assert isinstance(OpType.CAST_ON, str)


class TestOperation:
    def test_construction(self):
        op = Operation(
            op_type=OpType.WORK_EVEN,
            parameters={"pattern": "stockinette"},
            row_count=20,
            stitch_count_after=80,
            notes="main body section",
        )
        assert op.op_type == OpType.WORK_EVEN
        assert op.parameters["pattern"] == "stockinette"
        assert op.row_count == 20
        assert op.stitch_count_after == 80

    def test_is_frozen(self):
        op = Operation(
            op_type=OpType.CAST_ON,
            parameters={"count": 100},
            row_count=None,
            stitch_count_after=100,
        )
        with pytest.raises(Exception):
            op.row_count = 5  # type: ignore[misc]

    def test_optional_fields_default_none(self):
        op = Operation(
            op_type=OpType.BIND_OFF,
            parameters={},
            row_count=None,
            stitch_count_after=None,
        )
        assert op.row_count is None
        assert op.stitch_count_after is None
        assert op.notes == ""


class TestComponentIR:
    def _simple_stockinette_ir(self) -> ComponentIR:
        """Minimal valid IR: CAST_ON → WORK_EVEN → BIND_OFF."""
        cast_on = make_cast_on(80)
        work_even = make_work_even(row_count=40, stitch_count=80)
        bind_off = make_bind_off(80)
        return ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(cast_on, work_even, bind_off),
            starting_stitch_count=80,
            ending_stitch_count=0,
        )

    def test_construction(self):
        ir = self._simple_stockinette_ir()
        assert ir.component_name == "body"
        assert ir.handedness == Handedness.NONE
        assert len(ir.operations) == 3

    def test_is_frozen(self):
        ir = self._simple_stockinette_ir()
        with pytest.raises(Exception):
            ir.component_name = "sleeve"  # type: ignore[misc]

    def test_operations_are_parameterized_not_row_by_row(self):
        """Operations should span multiple rows — not one op per row."""
        ir = self._simple_stockinette_ir()
        work_even_op = ir.operations[1]
        assert work_even_op.op_type == OpType.WORK_EVEN
        assert work_even_op.row_count == 40
        assert len(ir.operations) == 3  # not 40 individual row ops

    def test_cast_on_to_work_even_to_bind_off_sequence(self):
        ir = self._simple_stockinette_ir()
        assert ir.operations[0].op_type == OpType.CAST_ON
        assert ir.operations[1].op_type == OpType.WORK_EVEN
        assert ir.operations[2].op_type == OpType.BIND_OFF

    def test_handedness_annotation_present(self):
        cast_on = make_cast_on(60)
        bind_off = make_bind_off(60)
        ir = ComponentIR(
            component_name="left_sleeve",
            handedness=Handedness.LEFT,
            operations=(cast_on, bind_off),
            starting_stitch_count=60,
            ending_stitch_count=0,
        )
        assert ir.handedness == Handedness.LEFT

    def test_stitch_count_tracking(self):
        ir = self._simple_stockinette_ir()
        assert ir.starting_stitch_count == 80
        assert ir.ending_stitch_count == 0

    def test_operations_are_tuple(self):
        ir = self._simple_stockinette_ir()
        assert isinstance(ir.operations, tuple)


class TestConvenienceFactories:
    def test_make_cast_on(self):
        op = make_cast_on(100)
        assert op.op_type == OpType.CAST_ON
        assert op.parameters["count"] == 100
        assert op.stitch_count_after == 100
        assert op.row_count is None

    def test_make_work_even(self):
        op = make_work_even(row_count=20, stitch_count=80)
        assert op.op_type == OpType.WORK_EVEN
        assert op.row_count == 20
        assert op.stitch_count_after == 80

    def test_make_bind_off(self):
        op = make_bind_off(80)
        assert op.op_type == OpType.BIND_OFF
        assert op.parameters["count"] == 80
        assert op.stitch_count_after == 0
