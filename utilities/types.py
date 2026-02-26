"""
Core type definitions for the shared utilities layer.

All types are frozen dataclasses with fail-fast validation in __post_init__.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Gauge:
    """
    Knitting gauge: stitch and row density per inch.

    Both values must be strictly positive. Gauges are immutable after
    construction and safe to share across modules.
    """

    stitches_per_inch: float
    rows_per_inch: float

    def __post_init__(self) -> None:
        if self.stitches_per_inch <= 0:
            raise ValueError(f"stitches_per_inch must be positive, got {self.stitches_per_inch}")
        if self.rows_per_inch <= 0:
            raise ValueError(f"rows_per_inch must be positive, got {self.rows_per_inch}")
