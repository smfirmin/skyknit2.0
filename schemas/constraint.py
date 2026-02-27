"""
Constraint object schema: knitting constraints flowing into Stitch Fillers.

The ConstraintObject bundles all knitting-physics inputs needed to convert
physical dimensions into valid stitch counts: gauge, stitch motif, hard
divisibility constraints, yarn metadata, and physical tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass

from utilities.types import Gauge


@dataclass(frozen=True)
class StitchMotif:
    """
    A repeating stitch pattern with horizontal and vertical repeat counts.

    Attributes:
        name: Human-readable name for the motif (e.g. "2x2 ribbing").
        stitch_repeat: Number of stitches in one horizontal repeat.
        row_repeat: Number of rows in one vertical repeat.
    """

    name: str
    stitch_repeat: int
    row_repeat: int


@dataclass(frozen=True)
class YarnSpec:
    """
    Yarn specification metadata.

    Attributes:
        weight: Yarn weight category (e.g. "worsted", "DK").
        fiber: Fiber content description (e.g. "100% merino wool").
        needle_size_mm: Recommended needle diameter in mm.
    """

    weight: str
    fiber: str
    needle_size_mm: float


@dataclass(frozen=True)
class ConstraintObject:
    """
    Complete set of knitting constraints for a single component.

    Bundles gauge, stitch motif, hard divisibility requirements, yarn
    metadata, and physical tolerance. Passed into Stitch Fillers and the
    Algebraic Checker.

    ``gauge`` is imported from ``utilities`` — not a duplicate type.

    Attributes:
        gauge: Stitch and row density (from utilities.Gauge).
        stitch_motif: Repeating stitch pattern for this component.
        hard_constraints: Additional divisors the final stitch count must satisfy.
        yarn_spec: Yarn weight, fiber, and needle size.
        physical_tolerance_mm: Allowed physical deviation in mm.
    """

    gauge: Gauge
    stitch_motif: StitchMotif
    hard_constraints: tuple[int, ...]
    yarn_spec: YarnSpec
    physical_tolerance_mm: float
