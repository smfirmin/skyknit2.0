"""
Stitch count resolver for the Stitch Fillers layer.

resolve_stitch_counts converts each edge's physical dimension into a stitch
count using the shared utilities pipeline (identical to the one used by the
Algebraic Checker — they must never diverge).

Dimension-to-edge mapping by shape type (positional fallback):
  CYLINDER   — single circumference_mm applies to every circumferential edge
  TRAPEZOID  — top_circumference_mm for the top edge, bottom_circumference_mm
               for the bottom edge (by convention: first edge = top)
  RECTANGLE  — width_mm applies to every horizontal edge

Named routing (takes precedence when set):
  If Edge.dimension_key is not None, that key is looked up directly in the
  component's dimensions dict, bypassing positional inference.  Use this for
  components with more than two horizontal edges, or where edge order does not
  match the positional convention.

Edges whose dimension cannot be inferred from the component's dimension dict
(e.g. a SELVEDGE or OPEN edge with no matching key) are mapped to None in the
returned dict, signalling that escalation to the LLM layer is needed.
"""

from __future__ import annotations

from schemas.constraint import ConstraintObject
from schemas.manifest import ComponentSpec, ShapeType
from topology.types import EdgeType
from utilities.repeats import select_stitch_count_from_physical


def resolve_stitch_counts(
    component_spec: ComponentSpec,
    constraint: ConstraintObject,
) -> dict[str, int | None]:
    """
    Resolve each named edge to its stitch count.

    Parameters
    ----------
    component_spec:
        The component whose edges are being resolved.
    constraint:
        Gauge, tolerance, stitch motif, and hard constraints for this component.

    Returns
    -------
    A dict mapping edge name → stitch count (int), or None if the count
    cannot be determined deterministically from the available dimensions.
    """
    result: dict[str, int | None] = {}
    dim = component_spec.dimensions
    gauge = constraint.gauge
    tolerance_mm = constraint.physical_tolerance_mm
    stitch_repeat = constraint.stitch_motif.stitch_repeat
    hard = list(constraint.hard_constraints) if constraint.hard_constraints else None

    for idx, edge in enumerate(component_spec.edges):
        dimension_mm = _resolve_dimension(
            component_spec.shape_type, dim, edge.edge_type, idx, edge.dimension_key
        )
        if dimension_mm is None:
            result[edge.name] = None
        else:
            result[edge.name] = select_stitch_count_from_physical(
                dimension_mm=dimension_mm,
                gauge=gauge,
                tolerance_mm=tolerance_mm,
                stitch_repeat=stitch_repeat,
                hard_constraints=hard,
            )

    return result


# ── Dimension inference ────────────────────────────────────────────────────────


def _resolve_dimension(
    shape_type: ShapeType,
    dimensions: object,  # MappingProxyType[str, float]
    edge_type: EdgeType,
    edge_index: int,
    dimension_key: str | None = None,
) -> float | None:
    """
    Return the physical dimension (mm) for a specific edge, or None.

    If *dimension_key* is provided, it is looked up directly in *dimensions*
    (named routing).  Otherwise, the mapping falls back to shape_type + edge
    position (positional routing):
      CYLINDER   → circumference_mm (same for all edges)
      TRAPEZOID  → top_circumference_mm (index 0) / bottom_circumference_mm (index 1+)
      RECTANGLE  → width_mm (same for all edges)

    SELVEDGE edges are lateral (row-based) and have no stitch dimension → None,
    regardless of routing mode.
    """
    from types import MappingProxyType

    dims: dict[str, float]
    if isinstance(dimensions, MappingProxyType):
        dims = dict(dimensions)
    else:
        dims = dict(dimensions)  # type: ignore[arg-type]

    # Lateral edges have no stitch-count dimension
    if edge_type == EdgeType.SELVEDGE:
        return None

    # Named routing takes precedence when dimension_key is set
    if dimension_key is not None:
        return dims.get(dimension_key)

    # Positional fallback
    match shape_type:
        case ShapeType.CYLINDER:
            return dims.get("circumference_mm")
        case ShapeType.TRAPEZOID:
            if edge_index == 0:
                return dims.get("top_circumference_mm")
            else:
                return dims.get("bottom_circumference_mm")
        case ShapeType.RECTANGLE:
            return dims.get("width_mm")

    return None
