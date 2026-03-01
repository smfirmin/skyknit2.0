"""
Intra-component simulation and edge stitch count extraction for the Algebraic Checker.

simulate_component replays a ComponentIR's operations through the VM and
verifies that the declared stitch counts match the simulated ones.  It
returns a SimulationResult rather than raising so the caller can collect
errors from all components before reporting.

extract_edge_counts maps each named edge in a ComponentSpec to its stitch
count, using the simulation result to resolve held/separated stitches.

CheckerError carries enough context for a user-facing message:
  - component_name: which garment piece failed
  - operation_index: position of the offending operation in the IR (0-based)
  - message: human-readable description of the problem
  - error_type: "filler_origin" (bad arithmetic from the Stitch Filler) or
                "geometric_origin" (declared measurements mismatch)
"""

from __future__ import annotations

from dataclasses import dataclass

from skyknit.checker.operations import execute_op
from skyknit.checker.vm_state import VMState
from skyknit.schemas.ir import ComponentIR, OpType
from skyknit.schemas.manifest import ComponentSpec
from skyknit.topology.types import EdgeType, Join, JoinType


@dataclass(frozen=True)
class CheckerError:
    """A single validation failure within a component simulation."""

    component_name: str
    operation_index: int
    message: str
    error_type: str  # "filler_origin" | "geometric_origin"


@dataclass(frozen=True)
class SimulationResult:
    """Outcome of simulating one ComponentIR."""

    passed: bool
    final_state: VMState
    errors: tuple[CheckerError, ...]


def simulate_component(ir: ComponentIR) -> SimulationResult:
    """
    Replay all operations in *ir* through the VM and validate stitch counts.

    Validation checks (in order):
    1. For CAST_ON components: ``starting_stitch_count`` must match the count
       established by the CAST_ON operation.
       For PICKUP_STITCHES / CONTINUATION components: the VM is pre-loaded
       with ``starting_stitch_count`` live stitches (0 for PICKUP_STITCHES,
       which then adds stitches via the operation itself).
    2. Each operation must execute without raising ValueError.
    3. ``ending_stitch_count`` must match the VM's live count after all ops.

    Returns a SimulationResult with ``passed=True`` when all checks pass,
    or ``passed=False`` with one or more CheckerErrors describing each
    failure.
    """
    # Receiving components begin with live stitches already on the needle.
    # CAST_ON components start from zero and explicitly establish their count.
    first_op_is_cast_on = len(ir.operations) > 0 and ir.operations[0].op_type == OpType.CAST_ON
    state = (
        VMState() if first_op_is_cast_on else VMState(live_stitch_count=ir.starting_stitch_count)
    )
    errors: list[CheckerError] = []

    for idx, op in enumerate(ir.operations):
        try:
            execute_op(state, op)
        except (ValueError, KeyError) as exc:
            errors.append(
                CheckerError(
                    component_name=ir.component_name,
                    operation_index=idx,
                    message=str(exc),
                    error_type="filler_origin",
                )
            )
            # Continue simulating — collect remaining errors
            continue

        # After CAST_ON, verify it matches the declared starting_stitch_count
        if idx == 0 and first_op_is_cast_on and state.live_stitch_count != ir.starting_stitch_count:
            errors.append(
                CheckerError(
                    component_name=ir.component_name,
                    operation_index=0,
                    message=(
                        f"declared starting_stitch_count ({ir.starting_stitch_count}) "
                        f"does not match CAST_ON count ({state.live_stitch_count})"
                    ),
                    error_type="geometric_origin",
                )
            )

    # Validate ending stitch count
    if state.live_stitch_count != ir.ending_stitch_count:
        errors.append(
            CheckerError(
                component_name=ir.component_name,
                operation_index=len(ir.operations) - 1,
                message=(
                    f"declared ending_stitch_count ({ir.ending_stitch_count}) "
                    f"does not match final live count ({state.live_stitch_count})"
                ),
                error_type="geometric_origin",
            )
        )

    return SimulationResult(
        passed=len(errors) == 0,
        final_state=state,
        errors=tuple(errors),
    )


def _total_row_count(ir: ComponentIR) -> int:
    """Sum the row_count of all operations in *ir* that declare one."""
    return sum(op.row_count for op in ir.operations if op.row_count is not None)


def extract_edge_counts(
    ir: ComponentIR,
    component_spec: ComponentSpec,
    joins: tuple[Join, ...] | None = None,
) -> dict[str, int]:
    """
    Map each named edge in *component_spec* to its stitch count.

    Strategy:
    - Edges whose name matches a HOLD/SEPARATE label in the IR → count from
      ``held_stitches`` in the final VM state.
    - ``BOUND_OFF`` / ``OPEN`` edges → ``ir.ending_stitch_count``.
    - ``LIVE_STITCH`` edges:
        - If the edge is the downstream end of a PICKUP join (join_type==PICKUP,
          edge_b belongs to this component), the pickup creates new stitches →
          ``ir.starting_stitch_count``.
        - If the IR's first operation is ``CAST_ON`` (and not a PICKUP downstream),
          the component produces its own stitches → ``ir.ending_stitch_count``.
        - Otherwise the component receives live stitches from upstream →
          ``ir.starting_stitch_count``.
    - ``CAST_ON`` edges → ``ir.starting_stitch_count``.
    - ``SELVEDGE`` edges → total row count of the IR (the selvedge is a row-edge,
      not a stitch-count edge; its value is used for RATIO join arithmetic).
    """
    result = simulate_component(ir)
    held = result.final_state.held_stitches

    first_op_is_cast_on = len(ir.operations) > 0 and ir.operations[0].op_type == OpType.CAST_ON

    # Build a lookup: join_id → Join, for PICKUP joins where this component is edge_b
    pickup_downstream_join_ids: set[str] = set()
    if joins is not None:
        for join in joins:
            if (
                join.join_type == JoinType.PICKUP
                and join.edge_b_ref.split(".")[0] == component_spec.name
            ):
                pickup_downstream_join_ids.add(join.id)

    edge_counts: dict[str, int] = {}
    for edge in component_spec.edges:
        if edge.name in held:
            edge_counts[edge.name] = held[edge.name]
        elif edge.edge_type in (EdgeType.BOUND_OFF, EdgeType.OPEN):
            edge_counts[edge.name] = ir.ending_stitch_count
        elif edge.edge_type == EdgeType.LIVE_STITCH:
            # PICKUP downstream: the pickup creates new stitches = starting count
            if edge.join_ref is not None and edge.join_ref in pickup_downstream_join_ids:
                edge_counts[edge.name] = ir.starting_stitch_count
            elif first_op_is_cast_on:
                edge_counts[edge.name] = ir.ending_stitch_count
            else:
                edge_counts[edge.name] = ir.starting_stitch_count
        elif edge.edge_type == EdgeType.SELVEDGE:
            # SELVEDGE is a row-edge (armhole side); its count is the total rows
            # worked, used as the source value in RATIO join validation.
            edge_counts[edge.name] = _total_row_count(ir)
        else:
            # CAST_ON edge
            edge_counts[edge.name] = ir.starting_stitch_count

    return edge_counts
