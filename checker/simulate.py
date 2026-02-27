"""
Intra-component simulation and edge stitch count extraction.

simulate_component runs an ordered operation sequence through the VM and
verifies that declared stitch counts match simulated values.

extract_edge_counts maps each named edge of a ComponentSpec to the stitch
count at its corresponding point in the IR execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from schemas.ir import ComponentIR, OpType
from schemas.manifest import ComponentSpec
from topology.types import EdgeType

from .operations import OperationError, execute_op
from .vm_state import VMState


class ErrorOrigin(str, Enum):
    """Classification of checker errors for upstream routing."""

    FILLER_ORIGIN = "filler_origin"
    GEOMETRIC_ORIGIN = "geometric_origin"


@dataclass(frozen=True)
class CheckerError:
    """
    A single error found during algebraic checking.

    Attributes:
        component_name: Which component the error belongs to.
        operation_index: Index of the offending operation (-1 for non-op errors).
        message: Human-readable description of the error.
        error_type: Classification for upstream routing.
    """

    component_name: str
    operation_index: int
    message: str
    error_type: ErrorOrigin


@dataclass(frozen=True)
class SimulationResult:
    """
    Result of simulating a single component's operation sequence.

    Attributes:
        passed: True if simulation completed without errors.
        final_state: The VM state after all operations (or at failure point).
        errors: List of errors found during simulation.
    """

    passed: bool
    final_state: VMState
    errors: tuple[CheckerError, ...]


def simulate_component(ir: ComponentIR) -> SimulationResult:
    """
    Execute all operations in a ComponentIR and validate consistency.

    Checks:
    - First operation's stitch count matches ``starting_stitch_count``
    - Each operation executes without error
    - Final stitch count matches ``ending_stitch_count``
    """
    errors: list[CheckerError] = []
    state = VMState(live_stitch_count=0)

    if not ir.operations:
        errors.append(
            CheckerError(
                component_name=ir.component_name,
                operation_index=-1,
                message="ComponentIR has no operations",
                error_type=ErrorOrigin.FILLER_ORIGIN,
            )
        )
        return SimulationResult(passed=False, final_state=state, errors=tuple(errors))

    # Validate first op is CAST_ON and matches starting_stitch_count
    first_op = ir.operations[0]
    if first_op.op_type == OpType.CAST_ON:
        cast_on_count = first_op.parameters.get("count", 0)
        if cast_on_count != ir.starting_stitch_count:
            errors.append(
                CheckerError(
                    component_name=ir.component_name,
                    operation_index=0,
                    message=(
                        f"CAST_ON count ({cast_on_count}) does not match "
                        f"declared starting_stitch_count ({ir.starting_stitch_count})"
                    ),
                    error_type=ErrorOrigin.FILLER_ORIGIN,
                )
            )
    elif first_op.op_type == OpType.PICKUP_STITCHES:
        # PICKUP_STITCHES is also a valid first operation
        pass
    else:
        errors.append(
            CheckerError(
                component_name=ir.component_name,
                operation_index=0,
                message=(
                    f"First operation must be CAST_ON or PICKUP_STITCHES, "
                    f"got {first_op.op_type.value}"
                ),
                error_type=ErrorOrigin.FILLER_ORIGIN,
            )
        )

    # Execute all operations
    for i, op in enumerate(ir.operations):
        try:
            state = execute_op(state, op)
        except OperationError as exc:
            errors.append(
                CheckerError(
                    component_name=ir.component_name,
                    operation_index=i,
                    message=str(exc),
                    error_type=ErrorOrigin.FILLER_ORIGIN,
                )
            )
            return SimulationResult(passed=False, final_state=state, errors=tuple(errors))

    # Validate ending stitch count
    if state.live_stitch_count != ir.ending_stitch_count:
        errors.append(
            CheckerError(
                component_name=ir.component_name,
                operation_index=len(ir.operations) - 1,
                message=(
                    f"Final live stitch count ({state.live_stitch_count}) does not match "
                    f"declared ending_stitch_count ({ir.ending_stitch_count})"
                ),
                error_type=ErrorOrigin.FILLER_ORIGIN,
            )
        )

    return SimulationResult(
        passed=len(errors) == 0,
        final_state=state,
        errors=tuple(errors),
    )


def extract_edge_counts(ir: ComponentIR, component_spec: ComponentSpec) -> dict[str, int]:
    """
    Map each named edge of a ComponentSpec to its stitch count from the IR.

    Convention:
    - CAST_ON edges get ``starting_stitch_count``
    - BOUND_OFF / OPEN edges get ``ending_stitch_count``
    - LIVE_STITCH edges get the stitch count at the point of hold/separate
    - SELVEDGE edges are not assigned stitch counts (omitted from result)

    The returned dict is keyed by ``"component_name.edge_name"``.
    """
    edge_counts: dict[str, int] = {}

    for edge in component_spec.edges:
        ref = f"{component_spec.name}.{edge.name}"

        if edge.edge_type == EdgeType.CAST_ON:
            edge_counts[ref] = ir.starting_stitch_count

        elif edge.edge_type in (EdgeType.BOUND_OFF, EdgeType.OPEN):
            edge_counts[ref] = ir.ending_stitch_count

        elif edge.edge_type == EdgeType.LIVE_STITCH:
            # Live stitch edges represent intermediate points; use stitch
            # count at hold/separate operations that target this edge.
            # Default to ending_stitch_count if no specific hold is found.
            count = _find_edge_stitch_count(ir, edge.name)
            edge_counts[ref] = count if count is not None else ir.ending_stitch_count

        # SELVEDGE edges don't carry stitch counts — omitted

    return edge_counts


def _find_edge_stitch_count(ir: ComponentIR, edge_name: str) -> int | None:
    """
    Search the IR for a HOLD or SEPARATE operation that references the given edge name.

    Returns the stitch count moved to that edge, or None if not found.
    """
    for op in ir.operations:
        if op.op_type == OpType.HOLD:
            if op.parameters.get("label") == edge_name:
                return int(op.parameters.get("count", 0))
        elif op.op_type == OpType.SEPARATE:
            groups: dict[str, int] = op.parameters.get("groups", {})
            if edge_name in groups:
                return int(groups[edge_name])
    return None
