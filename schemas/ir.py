"""
Intermediate Representation (IR) schema: the output contract of Stitch Fillers.

ComponentIR is a typed operation sequence for a single component instance.
Operations are parameterized (not flattened row-by-row). Handedness is
imported from schemas.manifest to avoid duplication.

The Algebraic Checker consumes these types as its primary input.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from schemas.manifest import Handedness


class OpType(str, Enum):
    """All valid IR operation types for top-down sweater construction."""

    CAST_ON = "CAST_ON"
    INCREASE_SECTION = "INCREASE_SECTION"
    WORK_EVEN = "WORK_EVEN"
    DECREASE_SECTION = "DECREASE_SECTION"
    SEPARATE = "SEPARATE"
    TAPER = "TAPER"
    BIND_OFF = "BIND_OFF"
    HOLD = "HOLD"
    PICKUP_STITCHES = "PICKUP_STITCHES"


@dataclass(frozen=True)
class Operation:
    """
    A single parameterized knitting operation.

    parameters: op-specific key/value data (e.g. {"cast_on_count": 120}
        for CAST_ON, {"shaping_intervals": [...]} for INCREASE_SECTION).
    row_count: number of rows this operation spans, or None for instantaneous ops.
    stitch_count_after: live stitch count after this operation completes, or None
        when the Algebraic Checker should infer it from context.
    notes: human-readable annotation for the Writer.
    """

    op_type: OpType
    parameters: dict[str, Any]
    row_count: int | None = None
    stitch_count_after: int | None = None
    notes: str = ""


@dataclass(frozen=True)
class ComponentIR:
    """
    Complete IR for one component instance.

    operations: tuple (not list) for immutability of the sequence reference.
    starting_stitch_count and ending_stitch_count are the declared boundary
    values; the Algebraic Checker validates that the operation sequence
    delivers exactly these counts.
    """

    component_name: str
    handedness: Handedness
    operations: tuple[Operation, ...]
    starting_stitch_count: int
    ending_stitch_count: int

    def __post_init__(self) -> None:
        if not self.component_name:
            raise ValueError("ComponentIR component_name must not be empty")
        if self.starting_stitch_count < 0:
            raise ValueError(
                f"starting_stitch_count must be non-negative, got {self.starting_stitch_count}"
            )
        if self.ending_stitch_count < 0:
            raise ValueError(
                f"ending_stitch_count must be non-negative, got {self.ending_stitch_count}"
            )
