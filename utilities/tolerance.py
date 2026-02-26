"""
Tolerance calculation from gauge, ease, and precision preference.

Tolerance is always expressed in physical units (mm). Stitch count
tolerances are derived from physical tolerance by downstream callers,
never set directly.

Formula:
    physical_tolerance_mm = gauge_base_mm × ease_multiplier × precision_multiplier
"""

from __future__ import annotations

from enum import Enum

from .conversion import MM_PER_INCH
from .types import Gauge

_EASE_MIN: float = 0.75
_EASE_MAX: float = 2.0


class PrecisionLevel(float, Enum):
    """Precision preference controlling tolerance band width."""

    HIGH = 0.75
    MEDIUM = 1.0
    LOW = 1.5


def gauge_base_mm(gauge: Gauge) -> float:
    """One stitch-width in mm at the given gauge."""
    return MM_PER_INCH / gauge.stitches_per_inch


def calculate_tolerance_mm(
    gauge: Gauge,
    ease_multiplier: float,
    precision: PrecisionLevel,
) -> float:
    """
    Derive physical tolerance in mm from gauge, ease, and precision.

    Args:
        gauge: Stitch and row density.
        ease_multiplier: Ease factor in [0.75, 2.0].
        precision: Precision preference (HIGH, MEDIUM, LOW).

    Returns:
        Tolerance in mm.

    Raises:
        ValueError: If ease_multiplier is outside [0.75, 2.0].
    """
    if not (_EASE_MIN <= ease_multiplier <= _EASE_MAX):
        raise ValueError(
            f"ease_multiplier must be in [{_EASE_MIN}, {_EASE_MAX}], got {ease_multiplier}"
        )
    return gauge_base_mm(gauge) * ease_multiplier * precision.value
