"""Tests for checker.simulate — intra-component simulation and edge extraction."""

import pytest

from checker.simulate import (
    CheckerError,
    extract_edge_counts,
    simulate_component,
)
from schemas.ir import ComponentIR, Operation, OpType, make_bind_off, make_cast_on, make_work_even
from schemas.manifest import ComponentSpec, Handedness, ShapeType
from topology.types import Edge, EdgeType


class TestSimulateComponent:
    def _simple_ir(self) -> ComponentIR:
        """CAST_ON -> WORK_EVEN -> BIND_OFF."""
        return ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(80),
                make_work_even(row_count=40, stitch_count=80),
                make_bind_off(80),
            ),
            starting_stitch_count=80,
            ending_stitch_count=0,
        )

    def test_valid_simple_component_passes(self):
        result = simulate_component(self._simple_ir())
        assert result.passed is True
        assert len(result.errors) == 0

    def test_final_state_correct(self):
        result = simulate_component(self._simple_ir())
        assert result.final_state.live_stitch_count == 0
        assert result.final_state.row_counter == 40

    def test_stitch_count_mismatch_at_end(self):
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(80),
                make_work_even(row_count=40, stitch_count=80),
                make_bind_off(80),
            ),
            starting_stitch_count=80,
            ending_stitch_count=80,  # wrong: bind_off leaves 0
        )
        result = simulate_component(ir)
        assert result.passed is False
        assert any("ending_stitch_count" in e.message for e in result.errors)

    def test_declared_starting_count_mismatch(self):
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(80),
                make_work_even(row_count=40, stitch_count=80),
                make_bind_off(80),
            ),
            starting_stitch_count=100,  # doesn't match CAST_ON(80)
            ending_stitch_count=0,
        )
        result = simulate_component(ir)
        assert result.passed is False
        assert any("starting_stitch_count" in e.message for e in result.errors)

    def test_invalid_first_operation(self):
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(
                make_bind_off(80),
                make_cast_on(80),
            ),
            starting_stitch_count=80,
            ending_stitch_count=80,
        )
        result = simulate_component(ir)
        assert result.passed is False
        assert any("First operation" in e.message for e in result.errors)

    def test_empty_operations(self):
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(),
            starting_stitch_count=0,
            ending_stitch_count=0,
        )
        result = simulate_component(ir)
        assert result.passed is False
        assert any("no operations" in e.message for e in result.errors)

    def test_errors_are_filler_origin(self):
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(80),
                make_bind_off(80),
            ),
            starting_stitch_count=80,
            ending_stitch_count=80,  # should be 0
        )
        result = simulate_component(ir)
        assert all(e.error_type == "filler_origin" for e in result.errors)

    def test_simulation_result_is_frozen(self):
        result = simulate_component(self._simple_ir())
        with pytest.raises(Exception):
            result.passed = False  # type: ignore[misc]

    def test_checker_error_is_frozen(self):
        error = CheckerError(
            component_name="body",
            operation_index=0,
            message="test",
            error_type="filler_origin",
        )
        with pytest.raises(Exception):
            error.message = "changed"  # type: ignore[misc]

    def test_increase_decrease_sequence(self):
        """CAST_ON -> INCREASE -> DECREASE -> BIND_OFF."""
        ir = ComponentIR(
            component_name="sleeve",
            handedness=Handedness.LEFT,
            operations=(
                make_cast_on(40),
                Operation(
                    op_type=OpType.INCREASE_SECTION,
                    parameters={},
                    row_count=20,
                    stitch_count_after=60,
                ),
                Operation(
                    op_type=OpType.DECREASE_SECTION,
                    parameters={},
                    row_count=20,
                    stitch_count_after=40,
                ),
                make_bind_off(40),
            ),
            starting_stitch_count=40,
            ending_stitch_count=0,
        )
        result = simulate_component(ir)
        assert result.passed is True


class TestExtractEdgeCounts:
    def _simple_component_spec(self) -> ComponentSpec:
        return ComponentSpec(
            name="body",
            shape_type=ShapeType.RECTANGLE,
            dimensions={"width": 500.0, "height": 600.0},
            edges=(
                Edge(name="top", edge_type=EdgeType.CAST_ON),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
                Edge(name="left", edge_type=EdgeType.SELVEDGE),
                Edge(name="right", edge_type=EdgeType.SELVEDGE),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )

    def _simple_ir(self) -> ComponentIR:
        return ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(100),
                make_work_even(row_count=40, stitch_count=100),
                make_bind_off(100),
            ),
            starting_stitch_count=100,
            ending_stitch_count=0,
        )

    def test_cast_on_edge_gets_starting_count(self):
        counts = extract_edge_counts(self._simple_ir(), self._simple_component_spec())
        assert counts["body.top"] == 100

    def test_bound_off_edge_gets_ending_count(self):
        counts = extract_edge_counts(self._simple_ir(), self._simple_component_spec())
        assert counts["body.bottom"] == 0

    def test_selvedge_edges_omitted(self):
        counts = extract_edge_counts(self._simple_ir(), self._simple_component_spec())
        assert "body.left" not in counts
        assert "body.right" not in counts

    def test_live_stitch_edge_from_hold(self):
        spec = ComponentSpec(
            name="yoke",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference": 800.0},
            edges=(
                Edge(name="top", edge_type=EdgeType.CAST_ON),
                Edge(name="sleeve_hold", edge_type=EdgeType.LIVE_STITCH),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        ir = ComponentIR(
            component_name="yoke",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(160),
                Operation(
                    op_type=OpType.HOLD,
                    parameters={"label": "sleeve_hold", "count": 40},
                    row_count=None,
                    stitch_count_after=120,
                ),
                make_work_even(row_count=20, stitch_count=120),
                make_bind_off(120),
            ),
            starting_stitch_count=160,
            ending_stitch_count=0,
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["yoke.sleeve_hold"] == 40
        assert counts["yoke.top"] == 160
        assert counts["yoke.bottom"] == 0

    def test_intermediate_edge_from_separate(self):
        spec = ComponentSpec(
            name="yoke",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference": 800.0},
            edges=(
                Edge(name="top", edge_type=EdgeType.CAST_ON),
                Edge(name="front_body", edge_type=EdgeType.LIVE_STITCH),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        ir = ComponentIR(
            component_name="yoke",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(120),
                Operation(
                    op_type=OpType.SEPARATE,
                    parameters={
                        "groups": {"front_body": 60, "back_body": 60},
                        "active_group": "front_body",
                    },
                    row_count=None,
                    stitch_count_after=60,
                ),
                make_work_even(row_count=10, stitch_count=60),
                make_bind_off(60),
            ),
            starting_stitch_count=120,
            ending_stitch_count=0,
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["yoke.front_body"] == 60
