"""
Unit conversion between physical dimensions and stitch/row counts.

All physical dimensions are in millimeters unless otherwise noted.
All functions are pure — no side effects, no state.
"""

from __future__ import annotations

from .types import Gauge

MM_PER_INCH: float = 25.4


def inches_to_mm(inches: float) -> float:
    """Convert inches to millimeters."""
    return inches * MM_PER_INCH


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / MM_PER_INCH


def physical_to_stitch_count(dimension_mm: float, gauge: Gauge) -> float:
    """Convert a physical dimension (mm) to a raw (non-integer) stitch count."""
    return mm_to_inches(dimension_mm) * gauge.stitches_per_inch


def physical_to_row_count(dimension_mm: float, gauge: Gauge) -> float:
    """Convert a physical dimension (mm) to a raw (non-integer) row count."""
    return mm_to_inches(dimension_mm) * gauge.rows_per_inch


def stitch_count_to_physical(count: float, gauge: Gauge) -> float:
    """Convert a stitch count to a physical dimension in mm."""
    return inches_to_mm(count / gauge.stitches_per_inch)


def row_count_to_physical(count: float, gauge: Gauge) -> float:
    """Convert a row count to a physical dimension in mm."""
    return inches_to_mm(count / gauge.rows_per_inch)
