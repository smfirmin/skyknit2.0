"""
Proportion spec: the output contract of the Design Module.

ProportionSpec carries dimensionless ratios (no measurements, no stitch counts)
and a precision preference. PrecisionPreference mirrors utilities.PrecisionLevel
values but lives here as an independent schema-layer enum — the schemas package
has no dependency on utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PrecisionPreference(float, Enum):
    """User-facing precision preference controlling tolerance band width.

    Numeric values match utilities.PrecisionLevel for direct interoperability.
    """

    HIGH = 0.75
    MEDIUM = 1.0
    LOW = 1.5


@dataclass(frozen=True)
class ProportionSpec:
    """
    Dimensionless proportions from the Design Module.

    Ratios are pure numbers (e.g. sleeve_length / body_length = 0.65).
    No measurements, no stitch counts. Physical dimensions are derived
    by the Planner by multiplying ratios against body measurements.
    """

    ratios: dict[str, float]
    precision: PrecisionPreference

    def __post_init__(self) -> None:
        if not self.ratios:
            raise ValueError("ratios must not be empty")
        for key, value in self.ratios.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"ratio key must be a non-empty string, got {key!r}")
            if value < 0:
                raise ValueError(f"ratio value must be non-negative, got {key}={value}")
