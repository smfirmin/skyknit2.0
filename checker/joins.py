"""
Inter-component join validation for the Algebraic Checker.

validate_join checks one Join against a flat edge_counts dict keyed by
"component.edge" refs (e.g. "body.top", "yoke.bottom").  It uses the
topology registry's arithmetic implication for the join's type to determine
what the stitch counts on each side must satisfy.

validate_all_joins runs validate_join over every join in the manifest and
collects the resulting CheckerErrors (if any).

Arithmetic rules (from arithmetic_implications.yaml):
  ONE_TO_ONE  — edge_a count ≈ edge_b count (within tolerance)
  ADDITIVE    — edge_b count = edge_a count + join.parameters["cast_on_count"]
  RATIO       — edge_b count ≈ round(edge_a count × join.parameters["pickup_ratio"])
  STRUCTURAL  — both edges consumed and merged; counts must agree (within tolerance)
"""

from __future__ import annotations

from collections.abc import Iterable
from math import floor

from topology.registry import get_registry
from topology.types import ArithmeticImplication, Join
from utilities.conversion import stitch_count_to_physical
from utilities.types import Gauge
from checker.simulate import CheckerError


def validate_join(
    join: Join,
    edge_counts: dict[str, int],
    tolerance_mm: float,
    gauge: Gauge,
) -> CheckerError | None:
    """
    Validate one join against the supplied edge stitch counts.

    Returns ``None`` if the join is valid, or a ``CheckerError`` describing
    the first violation found.

    Parameters
    ----------
    join:
        The join to validate.
    edge_counts:
        Flat mapping of ``"component.edge"`` → stitch count, assembled by the
        caller from per-component ``extract_edge_counts`` results.
    tolerance_mm:
        Physical tolerance in mm; stitch-count differences are converted to mm
        before being compared to this threshold.
    gauge:
        Gauge used to convert stitch counts to physical measurements.
    """
    arith = get_registry().get_arithmetic(join.join_type)

    count_a = edge_counts.get(join.edge_a_ref)
    count_b = edge_counts.get(join.edge_b_ref)

    if count_a is None:
        return CheckerError(
            component_name=join.id,
            operation_index=-1,
            message=f"edge {join.edge_a_ref!r} not found in edge_counts",
            error_type="geometric_origin",
        )
    if count_b is None:
        return CheckerError(
            component_name=join.id,
            operation_index=-1,
            message=f"edge {join.edge_b_ref!r} not found in edge_counts",
            error_type="geometric_origin",
        )

    match arith:
        case ArithmeticImplication.ONE_TO_ONE:
            diff_mm = stitch_count_to_physical(abs(count_a - count_b), gauge)
            if diff_mm > tolerance_mm:
                return CheckerError(
                    component_name=join.id,
                    operation_index=-1,
                    message=(
                        f"ONE_TO_ONE join '{join.id}': "
                        f"edge_a ({join.edge_a_ref}) has {count_a} sts, "
                        f"edge_b ({join.edge_b_ref}) has {count_b} sts — "
                        f"difference {diff_mm:.1f}mm exceeds tolerance {tolerance_mm}mm"
                    ),
                    error_type="geometric_origin",
                )

        case ArithmeticImplication.ADDITIVE:
            cast_on_count = int(join.parameters["cast_on_count"])
            expected_b = count_a + cast_on_count
            if count_b != expected_b:
                return CheckerError(
                    component_name=join.id,
                    operation_index=-1,
                    message=(
                        f"ADDITIVE join '{join.id}': "
                        f"expected edge_b count {expected_b} "
                        f"(edge_a {count_a} + cast_on {cast_on_count}), "
                        f"got {count_b}"
                    ),
                    error_type="geometric_origin",
                )

        case ArithmeticImplication.RATIO:
            pickup_ratio = float(join.parameters["pickup_ratio"])
            expected_b = floor(count_a * pickup_ratio)
            diff_mm = stitch_count_to_physical(abs(count_b - expected_b), gauge)
            if diff_mm > tolerance_mm:
                return CheckerError(
                    component_name=join.id,
                    operation_index=-1,
                    message=(
                        f"RATIO join '{join.id}': "
                        f"expected ~{expected_b} sts "
                        f"(edge_a {count_a} × ratio {pickup_ratio}), "
                        f"got {count_b} — "
                        f"difference {diff_mm:.1f}mm exceeds tolerance {tolerance_mm}mm"
                    ),
                    error_type="geometric_origin",
                )

        case ArithmeticImplication.STRUCTURAL:
            diff_mm = stitch_count_to_physical(abs(count_a - count_b), gauge)
            if diff_mm > tolerance_mm:
                return CheckerError(
                    component_name=join.id,
                    operation_index=-1,
                    message=(
                        f"STRUCTURAL join '{join.id}': "
                        f"edge_a ({join.edge_a_ref}) has {count_a} sts, "
                        f"edge_b ({join.edge_b_ref}) has {count_b} sts — "
                        f"difference {diff_mm:.1f}mm exceeds tolerance {tolerance_mm}mm"
                    ),
                    error_type="geometric_origin",
                )

    return None


def validate_all_joins(
    joins: Iterable[Join],
    all_edge_counts: dict[str, int],
    tolerance_mm: float,
    gauge: Gauge,
) -> list[CheckerError]:
    """
    Run ``validate_join`` over every join and return all errors found.

    Parameters
    ----------
    joins:
        All joins from the ShapeManifest.
    all_edge_counts:
        Flat ``"component.edge"`` → stitch count mapping assembled from
        every component's ``extract_edge_counts`` result.
    tolerance_mm:
        Physical tolerance applied to every join check.
    gauge:
        Gauge used for mm conversions.
    """
    errors: list[CheckerError] = []
    for join in joins:
        error = validate_join(join, all_edge_counts, tolerance_mm, gauge)
        if error is not None:
            errors.append(error)
    return errors
