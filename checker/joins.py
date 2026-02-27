"""
Inter-component join validation for the Algebraic Checker.

Validates that stitch counts at joined edges satisfy the arithmetic
implications defined in the topology registry. Each join type has a
specific rule (ONE_TO_ONE, ADDITIVE, RATIO, STRUCTURAL) governing how
the stitch counts on its two edges must relate.
"""

from __future__ import annotations

from topology.registry import get_registry
from topology.types import ArithmeticImplication, Join
from utilities.conversion import physical_to_stitch_count
from utilities.types import Gauge

from .simulate import CheckerError


def validate_join(
    join: Join,
    edge_counts: dict[str, int],
    tolerance_mm: float,
    gauge: Gauge,
) -> CheckerError | None:
    """
    Validate a single join's stitch count constraint.

    Uses the topology registry to look up the arithmetic implication for
    the join type, then checks whether the two edge stitch counts satisfy
    the rule within tolerance.

    Returns None if valid, or a CheckerError if invalid.
    """
    registry = get_registry()
    implication = registry.get_arithmetic(join.join_type)

    edge_a_count = edge_counts.get(join.edge_a_ref)
    edge_b_count = edge_counts.get(join.edge_b_ref)

    if edge_a_count is None:
        return CheckerError(
            component_name=join.edge_a_ref.split(".")[0],
            operation_index=-1,
            message=f"Missing edge count for {join.edge_a_ref} in join {join.id}",
            error_type="geometric_origin",
        )
    if edge_b_count is None:
        return CheckerError(
            component_name=join.edge_b_ref.split(".")[0],
            operation_index=-1,
            message=f"Missing edge count for {join.edge_b_ref} in join {join.id}",
            error_type="geometric_origin",
        )

    tolerance_stitches = physical_to_stitch_count(tolerance_mm, gauge)

    if implication == ArithmeticImplication.ONE_TO_ONE:
        return _validate_one_to_one(join, edge_a_count, edge_b_count, tolerance_stitches)
    elif implication == ArithmeticImplication.ADDITIVE:
        return _validate_additive(join, edge_a_count, edge_b_count, tolerance_stitches)
    elif implication == ArithmeticImplication.RATIO:
        return _validate_ratio(join, edge_a_count, edge_b_count, tolerance_stitches)
    elif implication == ArithmeticImplication.STRUCTURAL:
        return _validate_structural(join, edge_a_count, edge_b_count, tolerance_stitches)
    else:
        return CheckerError(
            component_name=join.edge_a_ref.split(".")[0],
            operation_index=-1,
            message=f"Unknown arithmetic implication {implication} for join {join.id}",
            error_type="geometric_origin",
        )


def _validate_one_to_one(
    join: Join,
    edge_a_count: int,
    edge_b_count: int,
    tolerance_stitches: float,
) -> CheckerError | None:
    """Both edges must have equal stitch counts (within tolerance)."""
    if abs(edge_a_count - edge_b_count) > tolerance_stitches:
        return CheckerError(
            component_name=join.edge_a_ref.split(".")[0],
            operation_index=-1,
            message=(
                f"ONE_TO_ONE join {join.id}: edge counts do not match — "
                f"{join.edge_a_ref}={edge_a_count}, {join.edge_b_ref}={edge_b_count} "
                f"(tolerance: {tolerance_stitches:.1f} stitches)"
            ),
            error_type="filler_origin",
        )
    return None


def _validate_additive(
    join: Join,
    edge_a_count: int,
    edge_b_count: int,
    tolerance_stitches: float,
) -> CheckerError | None:
    """edge_b count = edge_a count + cast_on_count parameter."""
    cast_on_count = join.parameters.get("cast_on_count", 0)
    expected = edge_a_count + cast_on_count
    if abs(edge_b_count - expected) > tolerance_stitches:
        return CheckerError(
            component_name=join.edge_b_ref.split(".")[0],
            operation_index=-1,
            message=(
                f"ADDITIVE join {join.id}: expected {join.edge_b_ref}={expected} "
                f"({join.edge_a_ref}={edge_a_count} + cast_on_count={cast_on_count}), "
                f"got {edge_b_count} (tolerance: {tolerance_stitches:.1f} stitches)"
            ),
            error_type="filler_origin",
        )
    return None


def _validate_ratio(
    join: Join,
    edge_a_count: int,
    edge_b_count: int,
    tolerance_stitches: float,
) -> CheckerError | None:
    """edge_b count = edge_a count * pickup_ratio."""
    pickup_ratio = join.parameters.get("pickup_ratio", 1.0)
    expected = edge_a_count * pickup_ratio
    if abs(edge_b_count - expected) > tolerance_stitches:
        return CheckerError(
            component_name=join.edge_b_ref.split(".")[0],
            operation_index=-1,
            message=(
                f"RATIO join {join.id}: expected {join.edge_b_ref}={expected:.1f} "
                f"({join.edge_a_ref}={edge_a_count} * ratio={pickup_ratio}), "
                f"got {edge_b_count} (tolerance: {tolerance_stitches:.1f} stitches)"
            ),
            error_type="filler_origin",
        )
    return None


def _validate_structural(
    join: Join,
    edge_a_count: int,
    edge_b_count: int,
    tolerance_stitches: float,
) -> CheckerError | None:
    """Both edges consumed and merged — counts must agree within tolerance."""
    if abs(edge_a_count - edge_b_count) > tolerance_stitches:
        return CheckerError(
            component_name=join.edge_a_ref.split(".")[0],
            operation_index=-1,
            message=(
                f"STRUCTURAL join {join.id}: edge counts do not agree — "
                f"{join.edge_a_ref}={edge_a_count}, {join.edge_b_ref}={edge_b_count} "
                f"(tolerance: {tolerance_stitches:.1f} stitches)"
            ),
            error_type="filler_origin",
        )
    return None


def validate_all_joins(
    joins: tuple[Join, ...],
    all_edge_counts: dict[str, int],
    tolerance_mm: float,
    gauge: Gauge,
) -> list[CheckerError]:
    """
    Validate all joins against the collected edge stitch counts.

    Returns a list of CheckerErrors (empty if all joins are valid).
    """
    errors: list[CheckerError] = []
    for join in joins:
        error = validate_join(join, all_edge_counts, tolerance_mm, gauge)
        if error is not None:
            errors.append(error)
    return errors
