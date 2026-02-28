"""
Single-operation execution for the Algebraic Checker VM.

execute_op takes a VMState and an Operation, validates the operation is
legal given the current state, applies it, and returns the updated state.
It raises ValueError for any operation that would produce an invalid state
(e.g. negative live stitch count, holding more stitches than are live).

The caller (simulate_component) is responsible for catching ValueError and
converting it to a CheckerError with the appropriate operation index.
"""

from __future__ import annotations

from checker.vm_state import VMState
from schemas.ir import Operation, OpType


def execute_op(state: VMState, op: Operation) -> VMState:
    """
    Apply a single IR operation to the VM state.

    Mutates ``state`` in-place and returns it for call-chaining convenience.

    Raises:
        ValueError: If the operation is invalid given the current state
            (e.g. holding more stitches than are live, CAST_ON with negative
            count, or an operation that would produce negative live count).
        KeyError: If a required parameter is missing from op.parameters.
    """
    match op.op_type:
        case OpType.CAST_ON:
            _exec_cast_on(state, op)
        case OpType.WORK_EVEN:
            _exec_work_even(state, op)
        case OpType.INCREASE_SECTION:
            _exec_increase_section(state, op)
        case OpType.DECREASE_SECTION:
            _exec_decrease_section(state, op)
        case OpType.TAPER:
            _exec_decrease_section(state, op)  # TAPER behaves like DECREASE_SECTION in the VM
        case OpType.BIND_OFF:
            _exec_bind_off(state, op)
        case OpType.HOLD:
            _exec_hold(state, op)
        case OpType.SEPARATE:
            _exec_separate(state, op)
        case OpType.PICKUP_STITCHES:
            _exec_pickup_stitches(state, op)
    return state


# ── Individual operation handlers ─────────────────────────────────────────────


def _exec_cast_on(state: VMState, op: Operation) -> None:
    count = int(op.parameters["count"])
    if count < 0:
        raise ValueError(f"CAST_ON count must be >= 0, got {count}")
    state.live_stitch_count = count


def _exec_work_even(state: VMState, op: Operation) -> None:
    if op.row_count is None:
        raise ValueError("WORK_EVEN operation requires row_count")
    if op.row_count < 0:
        raise ValueError(f"WORK_EVEN row_count must be >= 0, got {op.row_count}")
    state.row_counter += op.row_count


def _exec_increase_section(state: VMState, op: Operation) -> None:
    if op.stitch_count_after is None:
        raise ValueError("INCREASE_SECTION requires stitch_count_after")
    if op.stitch_count_after < state.live_stitch_count:
        raise ValueError(
            f"INCREASE_SECTION stitch_count_after ({op.stitch_count_after}) "
            f"must be >= current live count ({state.live_stitch_count})"
        )
    if op.row_count is not None:
        state.row_counter += op.row_count
    state.live_stitch_count = op.stitch_count_after


def _exec_decrease_section(state: VMState, op: Operation) -> None:
    if op.stitch_count_after is None:
        raise ValueError("DECREASE_SECTION requires stitch_count_after")
    if op.stitch_count_after < 0:
        raise ValueError(
            f"DECREASE_SECTION stitch_count_after must be >= 0, got {op.stitch_count_after}"
        )
    if op.stitch_count_after > state.live_stitch_count:
        raise ValueError(
            f"DECREASE_SECTION stitch_count_after ({op.stitch_count_after}) "
            f"must be <= current live count ({state.live_stitch_count})"
        )
    if op.row_count is not None:
        state.row_counter += op.row_count
    state.live_stitch_count = op.stitch_count_after


def _exec_bind_off(state: VMState, op: Operation) -> None:
    count = op.parameters.get("count")
    if count is not None and int(count) != state.live_stitch_count:
        raise ValueError(
            f"BIND_OFF count ({count}) does not match live stitch count ({state.live_stitch_count})"
        )
    state.live_stitch_count = 0


def _exec_hold(state: VMState, op: Operation) -> None:
    count = int(op.parameters["count"])
    label = str(op.parameters["label"])
    if count < 0:
        raise ValueError(f"HOLD count must be >= 0, got {count}")
    if count > state.live_stitch_count:
        raise ValueError(
            f"HOLD count ({count}) exceeds live stitch count ({state.live_stitch_count})"
        )
    state.held_stitches[label] = count
    state.live_stitch_count -= count


def _exec_separate(state: VMState, op: Operation) -> None:
    # SEPARATE moves a portion of live stitches to a new group (like HOLD).
    # Parameters: count (stitches to separate), label (group identifier).
    count = int(op.parameters["count"])
    label = str(op.parameters["label"])
    if count < 0:
        raise ValueError(f"SEPARATE count must be >= 0, got {count}")
    if count > state.live_stitch_count:
        raise ValueError(
            f"SEPARATE count ({count}) exceeds live stitch count ({state.live_stitch_count})"
        )
    state.held_stitches[label] = count
    state.live_stitch_count -= count


def _exec_pickup_stitches(state: VMState, op: Operation) -> None:
    count = int(op.parameters["count"])
    if count < 0:
        raise ValueError(f"PICKUP_STITCHES count must be >= 0, got {count}")
    state.live_stitch_count += count
