"""
Pattern repeat arithmetic: stitch count validation and selection.

Finds valid stitch counts within a tolerance band that satisfy pattern
repeat divisibility and hard constraints, then selects the optimal count.
"""

from __future__ import annotations

import math

from .conversion import physical_to_stitch_count
from .types import Gauge


def find_valid_counts(
    raw_target: float,
    tolerance_stitches: float,
    stitch_repeat: int,
    hard_constraints: list[int] | None = None,
) -> list[int]:
    """
    Find all integer stitch counts within the tolerance band that are
    divisible by stitch_repeat and satisfy all hard constraints.

    Args:
        raw_target: Non-integer raw stitch count from gauge conversion.
        tolerance_stitches: Half-width of the tolerance band in stitches.
        stitch_repeat: Pattern repeat (count must be divisible by this).
        hard_constraints: Additional divisors the count must satisfy.

    Returns:
        Sorted list of valid integer stitch counts. Empty if none found.
    """
    if stitch_repeat < 1:
        raise ValueError(f"stitch_repeat must be >= 1, got {stitch_repeat}")
    if tolerance_stitches < 0:
        raise ValueError(f"tolerance_stitches must be >= 0, got {tolerance_stitches}")

    constraints = hard_constraints or []
    for c in constraints:
        if c < 1:
            raise ValueError(f"hard_constraints values must be >= 1, got {c}")

    # Compute the effective repeat: LCM of stitch_repeat and all hard constraints
    effective_repeat = stitch_repeat
    for c in constraints:
        effective_repeat = math.lcm(effective_repeat, c)

    low = raw_target - tolerance_stitches
    high = raw_target + tolerance_stitches

    # Find the first multiple of effective_repeat >= low
    if effective_repeat == 0:
        return []

    first = math.ceil(low / effective_repeat) * effective_repeat
    if first < 1:
        first = effective_repeat  # stitch counts must be positive

    result: list[int] = []
    count = first
    while count <= high:
        result.append(count)
        count += effective_repeat

    return result


def select_stitch_count(
    raw_target: float,
    tolerance_stitches: float,
    stitch_repeat: int,
    hard_constraints: list[int] | None = None,
) -> int | None:
    """
    Select the optimal stitch count from the valid counts within tolerance.

    Picks the count closest to raw_target. On a tie (two counts equidistant
    from target), prefers the larger count — a standard knitting convention
    that favours slightly more ease over slightly less.

    Returns:
        The selected stitch count, or None if no valid count exists
        (signalling that escalation is needed upstream).
    """
    valid = find_valid_counts(raw_target, tolerance_stitches, stitch_repeat, hard_constraints)
    if not valid:
        return None

    # Sort by distance to target, then by count descending (prefer larger on tie)
    return min(valid, key=lambda c: (abs(c - raw_target), -c))


def select_stitch_count_from_physical(
    dimension_mm: float,
    gauge: Gauge,
    tolerance_mm: float,
    stitch_repeat: int,
    hard_constraints: list[int] | None = None,
) -> int | None:
    """
    End-to-end pipeline: physical dimension (mm) to selected stitch count.

    Converts physical dimensions and tolerance to stitch-domain values,
    then delegates to select_stitch_count. This is the function used
    identically by both Stitch Fillers and the Algebraic Checker.

    Args:
        dimension_mm: Physical dimension in millimeters.
        gauge: Stitch and row density.
        tolerance_mm: Physical tolerance in millimeters.
        stitch_repeat: Pattern repeat divisor.
        hard_constraints: Additional divisors the count must satisfy.

    Returns:
        The selected stitch count, or None if no valid count exists.
    """
    raw_target = physical_to_stitch_count(dimension_mm, gauge)
    tolerance_stitches = physical_to_stitch_count(tolerance_mm, gauge)
    return select_stitch_count(raw_target, tolerance_stitches, stitch_repeat, hard_constraints)
