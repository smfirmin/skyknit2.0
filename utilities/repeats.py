"""
Pattern repeat arithmetic: stitch count validation and selection.

Finds valid stitch counts within a tolerance band that satisfy pattern
repeat divisibility and hard constraints, then selects the optimal count.
"""

from __future__ import annotations

import math


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
