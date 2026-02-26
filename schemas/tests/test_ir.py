"""Tests for schemas.ir — ComponentIR, Operation, OpType."""

import pytest

from schemas.ir import ComponentIR, Operation, OpType
from schemas.manifest import Handedness


@pytest.fixture(scope="module")
def cast_on_op():
    return Operation(
        op_type=OpType.CAST_ON,
        parameters={"cast_on_count": 120},
        row_count=None,
        stitch_count_after=120,
        notes="Long-tail cast on",
    )


@pytest.fixture(scope="module")
def work_even_op():
    return Operation(
        op_type=OpType.WORK_EVEN,
        parameters={},
        row_count=80,
        stitch_count_after=120,
    )


@pytest.fixture(scope="module")
def bind_off_op():
    return Operation(
        op_type=OpType.BIND_OFF,
        parameters={},
        row_count=None,
        stitch_count_after=0,
    )


class TestOpType:
    def test_all_members_present(self):
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

    def test_is_str_enum(self):
        assert isinstance(OpType.CAST_ON, str)
        assert OpType.CAST_ON.value == "CAST_ON"


class TestOperation:
    def test_construction_full(self, cast_on_op):
        assert cast_on_op.op_type is OpType.CAST_ON
        assert cast_on_op.parameters == {"cast_on_count": 120}
        assert cast_on_op.row_count is None
        assert cast_on_op.stitch_count_after == 120
        assert cast_on_op.notes == "Long-tail cast on"

    def test_is_frozen(self, cast_on_op):
        with pytest.raises(AttributeError):
            cast_on_op.row_count = 5

    def test_optional_fields_default_to_none_and_empty(self):
        op = Operation(op_type=OpType.WORK_EVEN, parameters={})
        assert op.row_count is None
        assert op.stitch_count_after is None
        assert op.notes == ""

    def test_parameters_can_be_empty(self, work_even_op):
        assert work_even_op.parameters == {}

    def test_row_count_can_be_none(self, cast_on_op):
        """Instantaneous operations (CAST_ON, BIND_OFF) have no row_count."""
        assert cast_on_op.row_count is None

    def test_operations_are_parameterized_not_flat(self):
        """WORK_EVEN uses row_count, not one Operation per row."""
        op = Operation(
            op_type=OpType.WORK_EVEN,
            parameters={},
            row_count=40,
            stitch_count_after=100,
        )
        assert op.row_count == 40


class TestComponentIR:
    def test_minimal_stockinette_rectangle(self, cast_on_op, work_even_op, bind_off_op):
        """Construct CAST_ON → WORK_EVEN → BIND_OFF for a plain rectangle."""
        ir = ComponentIR(
            component_name="cuff",
            handedness=Handedness.NONE,
            operations=(cast_on_op, work_even_op, bind_off_op),
            starting_stitch_count=120,
            ending_stitch_count=0,
        )
        assert ir.component_name == "cuff"
        assert ir.handedness is Handedness.NONE
        assert len(ir.operations) == 3
        assert ir.operations[0].op_type is OpType.CAST_ON
        assert ir.operations[1].op_type is OpType.WORK_EVEN
        assert ir.operations[2].op_type is OpType.BIND_OFF
        assert ir.starting_stitch_count == 120
        assert ir.ending_stitch_count == 0

    def test_is_frozen(self, cast_on_op):
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(cast_on_op,),
            starting_stitch_count=120,
            ending_stitch_count=120,
        )
        with pytest.raises(AttributeError):
            ir.component_name = "torso"  # type: ignore[misc]

    def test_handedness_from_manifest(self, cast_on_op, bind_off_op):
        """Handedness is schemas.manifest.Handedness — not a redefined ir-level type."""
        from schemas.manifest import Handedness as ManifestHandedness

        ir = ComponentIR(
            component_name="sleeve_left",
            handedness=Handedness.LEFT,
            operations=(cast_on_op, bind_off_op),
            starting_stitch_count=80,
            ending_stitch_count=0,
        )
        assert isinstance(ir.handedness, ManifestHandedness)
        assert ir.handedness is ManifestHandedness.LEFT

    def test_left_handedness(self, cast_on_op, bind_off_op):
        ir = ComponentIR(
            component_name="sleeve_left",
            handedness=Handedness.LEFT,
            operations=(cast_on_op, bind_off_op),
            starting_stitch_count=80,
            ending_stitch_count=0,
        )
        assert ir.handedness is Handedness.LEFT

    def test_right_handedness(self, cast_on_op, bind_off_op):
        ir = ComponentIR(
            component_name="sleeve_right",
            handedness=Handedness.RIGHT,
            operations=(cast_on_op, bind_off_op),
            starting_stitch_count=80,
            ending_stitch_count=0,
        )
        assert ir.handedness is Handedness.RIGHT

    def test_operations_as_tuple(self, cast_on_op):
        """operations field is a tuple, not a list."""
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(cast_on_op,),
            starting_stitch_count=120,
            ending_stitch_count=120,
        )
        assert isinstance(ir.operations, tuple)

    def test_rejects_empty_component_name(self, cast_on_op):
        with pytest.raises(ValueError, match="component_name must not be empty"):
            ComponentIR(
                component_name="",
                handedness=Handedness.NONE,
                operations=(cast_on_op,),
                starting_stitch_count=120,
                ending_stitch_count=0,
            )

    def test_rejects_negative_starting_count(self, cast_on_op):
        with pytest.raises(ValueError, match="starting_stitch_count must be non-negative"):
            ComponentIR(
                component_name="body",
                handedness=Handedness.NONE,
                operations=(cast_on_op,),
                starting_stitch_count=-1,
                ending_stitch_count=0,
            )

    def test_shaping_ir_with_decrease(self, cast_on_op):
        """Verify DECREASE_SECTION can be constructed in an IR sequence."""
        decrease_op = Operation(
            op_type=OpType.DECREASE_SECTION,
            parameters={"intervals": [{"every_n_rows": 4, "times": 10}]},
            row_count=40,
            stitch_count_after=100,
        )
        ir = ComponentIR(
            component_name="sleeve",
            handedness=Handedness.LEFT,
            operations=(cast_on_op, decrease_op),
            starting_stitch_count=120,
            ending_stitch_count=100,
        )
        assert ir.operations[1].op_type is OpType.DECREASE_SECTION
