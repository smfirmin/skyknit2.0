"""Tests for checker.simulate — simulate_component, CheckerError, SimulationResult."""

from __future__ import annotations

import pytest

from checker.simulate import CheckerError, SimulationResult, simulate_component
from schemas.ir import ComponentIR, Operation, OpType, make_bind_off, make_cast_on, make_work_even
from schemas.manifest import Handedness


def _make_ir(
    operations: tuple,
    starting: int,
    ending: int,
    name: str = "body",
) -> ComponentIR:
    return ComponentIR(
        component_name=name,
        handedness=Handedness.NONE,
        operations=operations,
        starting_stitch_count=starting,
        ending_stitch_count=ending,
    )


class TestSimulationResult:
    def test_passed_result_has_no_errors(self):
        ir = _make_ir(
            (make_cast_on(80), make_work_even(row_count=20, stitch_count=80), make_bind_off(80)),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        assert result.passed is True
        assert result.errors == ()

    def test_final_state_reflects_execution(self):
        ir = _make_ir(
            (make_cast_on(80), make_work_even(row_count=20, stitch_count=80), make_bind_off(80)),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        assert result.final_state.live_stitch_count == 0
        assert result.final_state.row_counter == 20

    def test_result_is_frozen(self):
        ir = _make_ir(
            (make_cast_on(80), make_bind_off(80)),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        with pytest.raises(Exception):
            result.passed = False  # type: ignore[misc]


class TestCheckerError:
    def test_is_frozen(self):
        err = CheckerError(
            component_name="body",
            operation_index=0,
            message="something went wrong",
            error_type="filler_origin",
        )
        with pytest.raises(Exception):
            err.message = "updated"  # type: ignore[misc]


class TestSimulateValid:
    def test_cast_on_work_even_bind_off(self):
        ir = _make_ir(
            (make_cast_on(80), make_work_even(row_count=40, stitch_count=80), make_bind_off(80)),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        assert result.passed is True

    def test_minimal_cast_on_bind_off(self):
        ir = _make_ir(
            (make_cast_on(60), make_bind_off(60)),
            starting=60,
            ending=0,
        )
        result = simulate_component(ir)
        assert result.passed is True

    def test_returns_simulation_result_type(self):
        ir = _make_ir(
            (make_cast_on(80), make_bind_off(80)),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        assert isinstance(result, SimulationResult)


class TestSimulateErrors:
    def test_ending_stitch_count_mismatch(self):
        """IR declares ending=0 but BIND_OFF is missing → live count stays at 80."""
        ir = _make_ir(
            (make_cast_on(80), make_work_even(row_count=10, stitch_count=80)),
            starting=80,
            ending=0,  # wrong — live count will be 80, not 0
        )
        result = simulate_component(ir)
        assert result.passed is False
        assert len(result.errors) >= 1
        err = result.errors[-1]
        assert "ending_stitch_count" in err.message
        assert err.component_name == "body"
        assert err.error_type == "geometric_origin"

    def test_starting_stitch_count_mismatch(self):
        """IR declares starting=60 but CAST_ON establishes 80."""
        ir = _make_ir(
            (make_cast_on(80), make_bind_off(80)),
            starting=60,  # wrong
            ending=0,
        )
        result = simulate_component(ir)
        assert result.passed is False
        errors_about_start = [e for e in result.errors if "starting_stitch_count" in e.message]
        assert len(errors_about_start) >= 1

    def test_invalid_operation_produces_error(self):
        """BIND_OFF with wrong count → ValueError captured as CheckerError."""
        bad_bind_off = Operation(
            op_type=OpType.BIND_OFF,
            parameters={"count": 60},  # mismatch with live=80
            row_count=None,
            stitch_count_after=0,
        )
        ir = _make_ir(
            (make_cast_on(80), bad_bind_off),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        assert result.passed is False
        assert any("does not match" in e.message for e in result.errors)
        assert all(e.component_name == "body" for e in result.errors)

    def test_operation_error_has_correct_index(self):
        """Error operation_index should point to the offending operation."""
        bad_bind_off = Operation(
            op_type=OpType.BIND_OFF,
            parameters={"count": 60},
            row_count=None,
            stitch_count_after=0,
        )
        ir = _make_ir(
            (make_cast_on(80), bad_bind_off),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        op_errors = [e for e in result.errors if "does not match" in e.message]
        assert op_errors[0].operation_index == 1

    def test_multiple_errors_collected(self):
        """Errors in both operation execution and ending count are both collected."""
        bad_bind_off = Operation(
            op_type=OpType.BIND_OFF,
            parameters={"count": 60},  # wrong count → execution error
            row_count=None,
            stitch_count_after=0,
        )
        ir = _make_ir(
            (make_cast_on(80), bad_bind_off),
            starting=80,
            ending=0,
        )
        result = simulate_component(ir)
        # The execution error leaves live_stitch_count at 80 (bind_off failed),
        # and ending_stitch_count=0 doesn't match → two errors
        assert len(result.errors) >= 2
