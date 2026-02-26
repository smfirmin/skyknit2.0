"""
Constraint Object schema: the output contract of the Fabric Module.

One ConstraintObject is produced per component. It combines gauge,
stitch motif, hard constraints, yarn specification, and the derived
physical tolerance that controls stitch count selection precision.
"""

from __future__ import annotations

from dataclasses import dataclass

from utilities.types import Gauge


@dataclass(frozen=True)
class StitchMotif:
    """A named stitch pattern with repeat dimensions."""

    name: str
    stitch_repeat: int
    row_repeat: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("StitchMotif name must not be empty")
        if self.stitch_repeat < 1:
            raise ValueError(f"stitch_repeat must be >= 1, got {self.stitch_repeat}")
        if self.row_repeat < 1:
            raise ValueError(f"row_repeat must be >= 1, got {self.row_repeat}")


@dataclass(frozen=True)
class YarnSpec:
    """Yarn specification: weight category, fiber content, and needle size."""

    weight: str
    fiber: str
    needle_size_mm: float

    def __post_init__(self) -> None:
        if not self.weight:
            raise ValueError("YarnSpec weight must not be empty")
        if not self.fiber:
            raise ValueError("YarnSpec fiber must not be empty")
        if self.needle_size_mm <= 0:
            raise ValueError(f"needle_size_mm must be positive, got {self.needle_size_mm}")


@dataclass(frozen=True)
class ConstraintObject:
    """
    Per-component fabric constraints from the Fabric Module.

    Gauge is the canonical Gauge from utilities — not redefined here.
    physical_tolerance_mm is derived upstream (gauge_base × ease × precision)
    and stored as a plain float in mm. Stitch count tolerances are always
    derived from this value by downstream callers, never stored directly.
    """

    gauge: Gauge
    stitch_motif: StitchMotif
    hard_constraints: tuple[int, ...]
    yarn_spec: YarnSpec
    physical_tolerance_mm: float

    def __post_init__(self) -> None:
        if self.physical_tolerance_mm < 0:
            raise ValueError(
                f"physical_tolerance_mm must be non-negative, got {self.physical_tolerance_mm}"
            )
        for c in self.hard_constraints:
            if c < 1:
                raise ValueError(f"hard_constraints values must be >= 1, got {c}")
