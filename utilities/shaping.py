"""
Shaping rate calculator: distribute increases/decreases evenly across a section.

Given the total stitch change needed and the number of rows available,
produces shaping intervals that distribute the work as evenly as possible.

When the division is uneven, two intervals are returned: one at the more
frequent rate and one at the less frequent rate, matching standard knitting
pattern conventions (e.g. "decrease every 4th row 7 times, then every 3rd
row 3 times").
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ShapingAction(str, Enum):
    """Direction of a shaping operation."""

    INCREASE = "increase"
    DECREASE = "decrease"


@dataclass(frozen=True)
class ShapingInterval:
    """A single shaping instruction: perform action every N rows, repeated M times."""

    action: ShapingAction
    every_n_rows: int
    times: int
    stitches_per_action: int


def calculate_shaping_intervals(
    stitch_delta: int,
    section_depth_rows: int,
    stitches_per_action: int = 2,
) -> list[ShapingInterval]:
    """
    Distribute shaping evenly across a section.

    Args:
        stitch_delta: Total stitch change. Positive = increases, negative = decreases.
        section_depth_rows: Number of rows available for shaping.
        stitches_per_action: Stitches changed per shaping row (default 2: one each side).

    Returns:
        List of ShapingInterval(s). Empty if stitch_delta is 0.
        One interval if shaping divides evenly, two if uneven.

    Raises:
        ValueError: If section_depth_rows < 1, stitches_per_action < 1,
            or there are not enough rows.
    """
    if stitch_delta == 0:
        return []

    if section_depth_rows < 1:
        raise ValueError(f"section_depth_rows must be >= 1, got {section_depth_rows}")
    if stitches_per_action < 1:
        raise ValueError(f"stitches_per_action must be >= 1, got {stitches_per_action}")

    action = ShapingAction.INCREASE if stitch_delta > 0 else ShapingAction.DECREASE
    abs_delta = abs(stitch_delta)

    if abs_delta % stitches_per_action != 0:
        raise ValueError(
            f"stitch_delta ({stitch_delta}) must be divisible by "
            f"stitches_per_action ({stitches_per_action})"
        )

    num_actions = abs_delta // stitches_per_action

    if num_actions > section_depth_rows:
        raise ValueError(
            f"Not enough rows ({section_depth_rows}) for {num_actions} shaping actions "
            f"(need at least 1 row per action)"
        )

    # Distribute rows as evenly as possible across actions.
    # base_interval = floor(rows / actions), remainder gets spread as shorter intervals.
    base_interval = section_depth_rows // num_actions
    remainder = section_depth_rows % num_actions

    if remainder == 0:
        # Perfect division: single interval
        return [
            ShapingInterval(
                action=action,
                every_n_rows=base_interval,
                times=num_actions,
                stitches_per_action=stitches_per_action,
            )
        ]

    # Uneven: two intervals.
    # `remainder` actions happen every (base_interval + 1) rows (less frequent),
    # `(num_actions - remainder)` actions happen every base_interval rows (more frequent).
    # Convention: list the more frequent (shorter) interval first, then less frequent.
    frequent_times = num_actions - remainder
    infrequent_times = remainder

    intervals: list[ShapingInterval] = []
    if frequent_times > 0:
        intervals.append(
            ShapingInterval(
                action=action,
                every_n_rows=base_interval,
                times=frequent_times,
                stitches_per_action=stitches_per_action,
            )
        )
    if infrequent_times > 0:
        intervals.append(
            ShapingInterval(
                action=action,
                every_n_rows=base_interval + 1,
                times=infrequent_times,
                stitches_per_action=stitches_per_action,
            )
        )

    return intervals
