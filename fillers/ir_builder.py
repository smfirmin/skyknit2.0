"""
IR builder for the Stitch Fillers layer.

build_component_ir converts resolved stitch counts + component metadata into
a ComponentIR ready for the Algebraic Checker.  For v1 it handles the three
basic shape patterns:

  CYLINDER / flat rectangle (equal top and bottom counts):
    CAST_ON → WORK_EVEN → BIND_OFF

  Tapered (decreasing, e.g. sleeve from shoulder to cuff):
    CAST_ON → TAPER → BIND_OFF

  Expanding (increasing, e.g. raglan yoke body section):
    CAST_ON → INCREASE_SECTION → BIND_OFF

mirror_component_ir produces the mirror-image variant of a ComponentIR:
  LEFT → RIGHT handedness, RIGHT → LEFT handedness.
  Shaping direction annotations in operation notes are flipped where present.
"""

from __future__ import annotations

from schemas.constraint import ConstraintObject
from schemas.ir import ComponentIR, Operation, OpType
from schemas.manifest import ComponentSpec, Handedness
from topology.types import Edge, EdgeType, Join
from utilities.conversion import physical_to_section_rows

# Edge types that carry stitch counts and define the structural start/end of a
# component's knitting work.  SELVEDGE and OPEN edges are lateral/terminal and
# are skipped when finding start and end edges.
_STRUCTURAL: frozenset[EdgeType] = frozenset(
    {EdgeType.CAST_ON, EdgeType.LIVE_STITCH, EdgeType.BOUND_OFF}
)


def build_component_ir(
    component_spec: ComponentSpec,
    stitch_counts: dict[str, int],
    constraint: ConstraintObject,
    joins: list[Join],
    handedness: Handedness,
) -> ComponentIR:
    """
    Build a ComponentIR from resolved stitch counts.

    Infers the correct operation sequence from the stitch counts at the
    component's first (start) and last (end) edges:

    - Equal counts → CAST_ON → WORK_EVEN → BIND_OFF
    - Decreasing   → CAST_ON → TAPER → BIND_OFF
    - Increasing   → CAST_ON → INCREASE_SECTION → BIND_OFF

    The section depth in rows is derived from the ``depth_mm`` dimension
    (if present) and the gauge row rate; defaults to 1 if absent.

    Parameters
    ----------
    component_spec:
        Shape and dimension metadata.
    stitch_counts:
        Edge name → resolved stitch count.  Both the start and end edge
        names must be present and non-None.
    constraint:
        Gauge and tolerance for unit conversion.
    joins:
        Joins that include this component's edges (unused in v1, reserved
        for future join-aware shaping).
    handedness:
        LEFT / RIGHT / NONE — annotated onto the ComponentIR.

    Raises
    ------
    ValueError:
        If a required stitch count is missing or None.
    """
    edges = component_spec.edges
    if not edges:
        raise ValueError(f"component '{component_spec.name}' has no edges")

    # Use only structural edges (CAST_ON, LIVE_STITCH, BOUND_OFF) as start/end.
    # SELVEDGE and OPEN edges are lateral/terminal and do not define the knitting work.
    structural: list[Edge] = [e for e in edges if e.edge_type in _STRUCTURAL]
    if not structural:
        raise ValueError(
            f"component '{component_spec.name}' has no structural edges (CAST_ON, LIVE_STITCH, BOUND_OFF)"
        )

    start_edge = structural[0]
    end_edge = structural[-1]

    start_count = stitch_counts.get(start_edge.name)
    end_count = stitch_counts.get(end_edge.name)

    if start_count is None:
        raise ValueError(
            f"stitch count for start edge '{start_edge.name}' is None — cannot build IR"
        )
    if end_count is None:
        raise ValueError(f"stitch count for end edge '{end_edge.name}' is None — cannot build IR")

    depth_mm = component_spec.dimensions.get("depth_mm", 0.0)
    row_count = max(1, physical_to_section_rows(depth_mm, constraint.gauge)) if depth_mm else 1

    ops = _build_ops(
        component_name=component_spec.name,
        start_count=start_count,
        end_count=end_count,
        row_count=row_count,
    )

    return ComponentIR(
        component_name=component_spec.name,
        handedness=handedness,
        operations=tuple(ops),
        starting_stitch_count=start_count,
        ending_stitch_count=0,  # BIND_OFF always ends at 0
    )


def mirror_component_ir(ir: ComponentIR) -> ComponentIR:
    """
    Return a mirrored copy of *ir* with LEFT↔RIGHT handedness swapped.

    Operation notes that contain directional shaping markers are also
    mirrored (``SSK`` ↔ ``k2tog``).  Stitch counts are identical.
    """
    mirrored_handedness = _mirror_handedness(ir.handedness)
    mirrored_ops = tuple(_mirror_op(op) for op in ir.operations)

    return ComponentIR(
        component_name=ir.component_name,
        handedness=mirrored_handedness,
        operations=mirrored_ops,
        starting_stitch_count=ir.starting_stitch_count,
        ending_stitch_count=ir.ending_stitch_count,
    )


# ── Internal builders ─────────────────────────────────────────────────────────


def _build_ops(
    component_name: str,
    start_count: int,
    end_count: int,
    row_count: int,
) -> list[Operation]:
    cast_on = Operation(
        op_type=OpType.CAST_ON,
        parameters={"count": start_count},
        row_count=None,
        stitch_count_after=start_count,
    )
    bind_off = Operation(
        op_type=OpType.BIND_OFF,
        parameters={"count": end_count},
        row_count=None,
        stitch_count_after=0,
    )

    if start_count == end_count:
        middle = Operation(
            op_type=OpType.WORK_EVEN,
            parameters={},
            row_count=row_count,
            stitch_count_after=start_count,
        )
    elif start_count > end_count:
        middle = Operation(
            op_type=OpType.TAPER,
            parameters={},
            row_count=row_count,
            stitch_count_after=end_count,
            notes=f"decrease from {start_count} to {end_count} over {row_count} rows",
        )
    else:
        middle = Operation(
            op_type=OpType.INCREASE_SECTION,
            parameters={},
            row_count=row_count,
            stitch_count_after=end_count,
            notes=f"increase from {start_count} to {end_count} over {row_count} rows",
        )

    return [cast_on, middle, bind_off]


# ── Mirror helpers ────────────────────────────────────────────────────────────


def _mirror_handedness(handedness: Handedness) -> Handedness:
    match handedness:
        case Handedness.LEFT:
            return Handedness.RIGHT
        case Handedness.RIGHT:
            return Handedness.LEFT
        case Handedness.NONE:
            return Handedness.NONE


def _mirror_op(op: Operation) -> Operation:
    """Swap SSK↔k2tog in notes to reflect mirrored shaping direction."""
    notes = op.notes
    if "SSK" in notes or "k2tog" in notes:
        notes = (
            notes.replace("SSK", "__K2TOG__").replace("k2tog", "SSK").replace("__K2TOG__", "k2tog")
        )
    return Operation(
        op_type=op.op_type,
        parameters=op.parameters,
        row_count=op.row_count,
        stitch_count_after=op.stitch_count_after,
        notes=notes,
    )
