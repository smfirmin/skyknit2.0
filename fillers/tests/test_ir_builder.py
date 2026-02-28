"""Tests for fillers.ir_builder — build_component_ir and mirror_component_ir."""

from __future__ import annotations

import pytest

from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from schemas.ir import ComponentIR, OpType
from schemas.manifest import ComponentSpec, Handedness, ShapeType
from topology.types import Edge, EdgeType
from utilities.types import Gauge
from fillers.ir_builder import build_component_ir, mirror_component_ir

# ── Shared fixtures ────────────────────────────────────────────────────────────

GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
CONSTRAINT = ConstraintObject(
    gauge=GAUGE,
    stitch_motif=StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1),
    hard_constraints=(),
    yarn_spec=YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0),
    physical_tolerance_mm=10.0,
)


def _cylinder_spec(name: str = "body") -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": 508.0, "depth_mm": 457.2},
        edges=(
            Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
            Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
        ),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


def _trapezoid_spec(name: str = "sleeve") -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.TRAPEZOID,
        dimensions={
            "top_circumference_mm": 508.0,
            "bottom_circumference_mm": 254.0,
            "depth_mm": 457.2,
        },
        edges=(
            Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
            Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
        ),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


class TestPlainRectangle:
    def test_equal_counts_produce_work_even(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        op_types = [op.op_type for op in ir.operations]
        assert op_types == [OpType.CAST_ON, OpType.WORK_EVEN, OpType.BIND_OFF]

    def test_cast_on_count_matches_start(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        assert ir.operations[0].parameters["count"] == 400

    def test_bind_off_count_matches_end(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        assert ir.operations[2].parameters["count"] == 400

    def test_row_count_derived_from_depth(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        work_even = ir.operations[1]
        assert work_even.row_count is not None
        assert work_even.row_count > 0

    def test_starting_stitch_count_set(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        assert ir.starting_stitch_count == 400

    def test_ending_stitch_count_is_zero(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        assert ir.ending_stitch_count == 0


class TestTaperedComponent:
    def test_decreasing_counts_produce_taper(self):
        spec = _trapezoid_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 200}, CONSTRAINT, [], Handedness.NONE)
        op_types = [op.op_type for op in ir.operations]
        assert op_types == [OpType.CAST_ON, OpType.TAPER, OpType.BIND_OFF]

    def test_taper_stitch_count_after(self):
        spec = _trapezoid_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 200}, CONSTRAINT, [], Handedness.NONE)
        taper = ir.operations[1]
        assert taper.stitch_count_after == 200

    def test_taper_bind_off_count(self):
        spec = _trapezoid_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 200}, CONSTRAINT, [], Handedness.NONE)
        assert ir.operations[2].parameters["count"] == 200


class TestExpandingComponent:
    def test_increasing_counts_produce_increase_section(self):
        spec = _trapezoid_spec()
        ir = build_component_ir(spec, {"top": 200, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        op_types = [op.op_type for op in ir.operations]
        assert op_types == [OpType.CAST_ON, OpType.INCREASE_SECTION, OpType.BIND_OFF]

    def test_increase_section_stitch_count_after(self):
        spec = _trapezoid_spec()
        ir = build_component_ir(spec, {"top": 200, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        inc = ir.operations[1]
        assert inc.stitch_count_after == 400


class TestHandedness:
    def test_handedness_propagated(self):
        spec = _trapezoid_spec("left_sleeve")
        ir = build_component_ir(spec, {"top": 400, "bottom": 200}, CONSTRAINT, [], Handedness.LEFT)
        assert ir.handedness == Handedness.LEFT

    def test_none_handedness_propagated(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        assert ir.handedness == Handedness.NONE

    def test_component_name_preserved(self):
        spec = _cylinder_spec("body")
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        assert ir.component_name == "body"


class TestMissingStitchCount:
    def test_none_start_count_raises(self):
        spec = _cylinder_spec()
        with pytest.raises(ValueError, match="top"):
            build_component_ir(spec, {"top": None, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)

    def test_missing_end_count_raises(self):
        spec = _cylinder_spec()
        with pytest.raises(ValueError, match="bottom"):
            build_component_ir(spec, {"top": 400}, CONSTRAINT, [], Handedness.NONE)


class TestMirrorComponentIR:
    def test_left_becomes_right(self):
        spec = _trapezoid_spec("left_sleeve")
        ir = build_component_ir(spec, {"top": 400, "bottom": 200}, CONSTRAINT, [], Handedness.LEFT)
        mirrored = mirror_component_ir(ir)
        assert mirrored.handedness == Handedness.RIGHT

    def test_right_becomes_left(self):
        spec = _trapezoid_spec("right_sleeve")
        ir = build_component_ir(spec, {"top": 400, "bottom": 200}, CONSTRAINT, [], Handedness.RIGHT)
        mirrored = mirror_component_ir(ir)
        assert mirrored.handedness == Handedness.LEFT

    def test_none_handedness_unchanged(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.NONE)
        mirrored = mirror_component_ir(ir)
        assert mirrored.handedness == Handedness.NONE

    def test_stitch_counts_identical(self):
        spec = _trapezoid_spec("left_sleeve")
        ir = build_component_ir(spec, {"top": 400, "bottom": 200}, CONSTRAINT, [], Handedness.LEFT)
        mirrored = mirror_component_ir(ir)
        assert mirrored.starting_stitch_count == ir.starting_stitch_count
        assert mirrored.ending_stitch_count == ir.ending_stitch_count

    def test_returns_new_ir_object(self):
        spec = _cylinder_spec()
        ir = build_component_ir(spec, {"top": 400, "bottom": 400}, CONSTRAINT, [], Handedness.LEFT)
        mirrored = mirror_component_ir(ir)
        assert mirrored is not ir

    def test_shaping_notes_mirrored(self):
        from schemas.ir import Operation
        op_with_ssk = Operation(
            op_type=OpType.TAPER,
            parameters={},
            row_count=40,
            stitch_count_after=200,
            notes="decrease using SSK at start, k2tog at end",
        )
        ir = ComponentIR(
            component_name="sleeve",
            handedness=Handedness.LEFT,
            operations=(op_with_ssk,),
            starting_stitch_count=400,
            ending_stitch_count=0,
        )
        mirrored = mirror_component_ir(ir)
        mirrored_notes = mirrored.operations[0].notes
        assert "k2tog" in mirrored_notes
        assert "SSK" in mirrored_notes
        # Directions should be swapped
        assert mirrored_notes != op_with_ssk.notes
