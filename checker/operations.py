"""
Single-operation execution for the Algebraic Checker VM.

Each IR operation is dispatched to a handler that updates VMState by computing
the new stitch count and advancing the row counter. Invalid transitions
(e.g. negative stitch counts, bind-off with no live stitches) raise
CheckerError via the simulation layer above.
"""

from __future__ import annotations

from collections.abc import Callable

from schemas.ir import Operation, OpType

from .vm_state import VMState

_OpHandler = Callable[["VMState", "Operation"], "VMState"]


class OperationError(Exception):
    """Raised when an operation produces an invalid VM state transition."""


def execute_op(state: VMState, op: Operation) -> VMState:
    """
    Execute a single IR operation against the current VM state.

    Returns a new VMState reflecting the operation's effect. Raises
    OperationError if the operation is invalid given the current state.
    """
    handler = _DISPATCH.get(op.op_type)
    if handler is None:
        raise OperationError(f"Unknown operation type: {op.op_type}")
    return handler(state, op)


def _exec_cast_on(state: VMState, op: Operation) -> VMState:
    count = op.parameters.get("count", 0)
    if count <= 0:
        raise OperationError(f"CAST_ON count must be positive, got {count}")
    if state.live_stitch_count > 0:
        raise OperationError(
            f"CAST_ON with {state.live_stitch_count} live stitches already on needles"
        )
    return VMState(
        live_stitch_count=count,
        held_stitches=dict(state.held_stitches),
        row_counter=state.row_counter,
        current_needle=state.current_needle,
    )


def _exec_work_even(state: VMState, op: Operation) -> VMState:
    row_count = op.row_count
    if row_count is None or row_count <= 0:
        raise OperationError(f"WORK_EVEN requires positive row_count, got {row_count}")
    return VMState(
        live_stitch_count=state.live_stitch_count,
        held_stitches=dict(state.held_stitches),
        row_counter=state.row_counter + row_count,
        current_needle=state.current_needle,
    )


def _exec_increase_section(state: VMState, op: Operation) -> VMState:
    row_count = op.row_count
    if row_count is None or row_count <= 0:
        raise OperationError(f"INCREASE_SECTION requires positive row_count, got {row_count}")
    stitch_count_after = op.stitch_count_after
    if stitch_count_after is None:
        raise OperationError("INCREASE_SECTION requires stitch_count_after")
    if stitch_count_after <= state.live_stitch_count:
        raise OperationError(
            f"INCREASE_SECTION must increase stitches: "
            f"{state.live_stitch_count} -> {stitch_count_after}"
        )
    return VMState(
        live_stitch_count=stitch_count_after,
        held_stitches=dict(state.held_stitches),
        row_counter=state.row_counter + row_count,
        current_needle=state.current_needle,
    )


def _exec_decrease_section(state: VMState, op: Operation) -> VMState:
    row_count = op.row_count
    if row_count is None or row_count <= 0:
        raise OperationError(f"DECREASE_SECTION requires positive row_count, got {row_count}")
    stitch_count_after = op.stitch_count_after
    if stitch_count_after is None:
        raise OperationError("DECREASE_SECTION requires stitch_count_after")
    if stitch_count_after >= state.live_stitch_count:
        raise OperationError(
            f"DECREASE_SECTION must decrease stitches: "
            f"{state.live_stitch_count} -> {stitch_count_after}"
        )
    if stitch_count_after < 0:
        raise OperationError(
            f"DECREASE_SECTION cannot produce negative stitches: {stitch_count_after}"
        )
    return VMState(
        live_stitch_count=stitch_count_after,
        held_stitches=dict(state.held_stitches),
        row_counter=state.row_counter + row_count,
        current_needle=state.current_needle,
    )


def _exec_bind_off(state: VMState, op: Operation) -> VMState:
    count = op.parameters.get("count", state.live_stitch_count)
    if count <= 0:
        raise OperationError(f"BIND_OFF count must be positive, got {count}")
    if count > state.live_stitch_count:
        raise OperationError(
            f"BIND_OFF count ({count}) exceeds live stitches ({state.live_stitch_count})"
        )
    return VMState(
        live_stitch_count=state.live_stitch_count - count,
        held_stitches=dict(state.held_stitches),
        row_counter=state.row_counter,
        current_needle=state.current_needle,
    )


def _exec_hold(state: VMState, op: Operation) -> VMState:
    label = op.parameters.get("label", "held")
    count = op.parameters.get("count", 0)
    if count <= 0:
        raise OperationError(f"HOLD count must be positive, got {count}")
    if count > state.live_stitch_count:
        raise OperationError(
            f"HOLD count ({count}) exceeds live stitches ({state.live_stitch_count})"
        )
    new_held = dict(state.held_stitches)
    new_held[label] = new_held.get(label, 0) + count
    return VMState(
        live_stitch_count=state.live_stitch_count - count,
        held_stitches=new_held,
        row_counter=state.row_counter,
        current_needle=state.current_needle,
    )


def _exec_separate(state: VMState, op: Operation) -> VMState:
    groups: dict[str, int] = op.parameters.get("groups", {})
    total = sum(groups.values())
    if total != state.live_stitch_count:
        raise OperationError(
            f"SEPARATE groups total ({total}) does not match "
            f"live stitches ({state.live_stitch_count})"
        )
    # The active group continues; others go to held
    active_group = op.parameters.get("active_group")
    if active_group is None or active_group not in groups:
        raise OperationError(
            f"SEPARATE requires an active_group that exists in groups, got {active_group!r}"
        )
    new_held = dict(state.held_stitches)
    for label, count in groups.items():
        if label != active_group:
            new_held[label] = new_held.get(label, 0) + count
    return VMState(
        live_stitch_count=groups[active_group],
        held_stitches=new_held,
        row_counter=state.row_counter,
        current_needle=state.current_needle,
    )


def _exec_pickup_stitches(state: VMState, op: Operation) -> VMState:
    count = op.parameters.get("count", 0)
    if count <= 0:
        raise OperationError(f"PICKUP_STITCHES count must be positive, got {count}")
    source = op.parameters.get("source")
    new_held = dict(state.held_stitches)
    if source and source in new_held:
        if new_held[source] < count:
            raise OperationError(
                f"PICKUP_STITCHES count ({count}) exceeds held stitches "
                f"for '{source}' ({new_held[source]})"
            )
        new_held[source] -= count
        if new_held[source] == 0:
            del new_held[source]
    return VMState(
        live_stitch_count=state.live_stitch_count + count,
        held_stitches=new_held,
        row_counter=state.row_counter,
        current_needle=state.current_needle,
    )


def _exec_taper(state: VMState, op: Operation) -> VMState:
    row_count = op.row_count
    if row_count is None or row_count <= 0:
        raise OperationError(f"TAPER requires positive row_count, got {row_count}")
    stitch_count_after = op.stitch_count_after
    if stitch_count_after is None:
        raise OperationError("TAPER requires stitch_count_after")
    if stitch_count_after < 0:
        raise OperationError(f"TAPER cannot produce negative stitches: {stitch_count_after}")
    return VMState(
        live_stitch_count=stitch_count_after,
        held_stitches=dict(state.held_stitches),
        row_counter=state.row_counter + row_count,
        current_needle=state.current_needle,
    )


_DISPATCH: dict[OpType, _OpHandler] = {
    OpType.CAST_ON: _exec_cast_on,
    OpType.WORK_EVEN: _exec_work_even,
    OpType.INCREASE_SECTION: _exec_increase_section,
    OpType.DECREASE_SECTION: _exec_decrease_section,
    OpType.BIND_OFF: _exec_bind_off,
    OpType.HOLD: _exec_hold,
    OpType.SEPARATE: _exec_separate,
    OpType.PICKUP_STITCHES: _exec_pickup_stitches,
    OpType.TAPER: _exec_taper,
}
