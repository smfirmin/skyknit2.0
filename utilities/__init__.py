"""
Shared utilities for the Skyknit knitting pattern generator.

Provides deterministic tools used identically by Stitch Fillers and the
Algebraic Checker: unit conversion, tolerance calculation, pattern repeat
arithmetic, and shaping rate distribution.
"""

from .conversion import (
    MM_PER_INCH,
    inches_to_mm,
    mm_to_inches,
    physical_to_row_count,
    physical_to_stitch_count,
    row_count_to_physical,
    stitch_count_to_physical,
)
from .repeats import (
    find_valid_counts,
    select_stitch_count,
    select_stitch_count_from_physical,
)
from .shaping import ShapingInterval, calculate_shaping_intervals
from .tolerance import PrecisionLevel, calculate_tolerance_mm, gauge_base_mm
from .types import Gauge

__all__ = [
    # types
    "Gauge",
    "PrecisionLevel",
    "ShapingInterval",
    # conversion
    "MM_PER_INCH",
    "inches_to_mm",
    "mm_to_inches",
    "physical_to_stitch_count",
    "physical_to_row_count",
    "stitch_count_to_physical",
    "row_count_to_physical",
    # tolerance
    "gauge_base_mm",
    "calculate_tolerance_mm",
    # repeats
    "find_valid_counts",
    "select_stitch_count",
    "select_stitch_count_from_physical",
    # shaping
    "calculate_shaping_intervals",
]
