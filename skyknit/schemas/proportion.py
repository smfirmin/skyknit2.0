"""
Proportion specification schema: dimensionless ratios for sweater component sizing.

PrecisionPreference mirrors utilities.PrecisionLevel and provides a bridge via
to_precision_level() so downstream modules never hand-code the mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from skyknit.utilities.tolerance import PrecisionLevel


class PrecisionPreference(str, Enum):
    """
    Preferred tolerance precision for this proportion spec.

    Maps directly to utilities.PrecisionLevel values:
      HIGH   → 0.75 (tightest band)
      MEDIUM → 1.0
      LOW    → 1.5  (widest band)
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    def to_precision_level(self) -> PrecisionLevel:
        """Return the corresponding utilities.PrecisionLevel for this preference."""
        return PrecisionLevel[self.name]


@dataclass(frozen=True)
class ProportionSpec:
    """
    Dimensionless ratio specification for sweater components.

    All values in ``ratios`` are pure ratios (no physical units).
    Physical dimensions are computed downstream by multiplying against
    body measurements.

    Attributes:
        ratios: Mapping of component/measurement names to dimensionless ratios.
        precision: Preferred precision for tolerance calculations.
    """

    ratios: MappingProxyType[str, float]
    precision: PrecisionPreference

    def __post_init__(self) -> None:
        # Ensure callers stored a MappingProxyType so ratios are immutable.
        if not isinstance(self.ratios, MappingProxyType):
            raise TypeError(f"ratios must be a MappingProxyType, got {type(self.ratios).__name__}")
