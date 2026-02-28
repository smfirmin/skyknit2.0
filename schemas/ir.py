"""
Intermediate Representation (IR) schema for knitting operations.

The IR is the parameterized, component-level representation of knitting
instructions. Operations are high-level (e.g. WORK_EVEN for N rows) — not
flattened row-by-row. The Writer translates IR into pattern prose.

ComponentIR is the unit of exchange between Stitch Fillers, the Algebraic
Checker, and the Writer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from schemas.manifest import Handedness


class OpType(str, Enum):
    """Parameterized knitting operation types."""

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
    A single parameterized knitting operation within a component.

    Attributes:
        op_type: The type of operation.
        parameters: Operation-specific parameters (e.g. shaping rates, pickup ratios).
        row_count: Number of rows consumed by this operation, or None if N/A.
        stitch_count_after: Live stitch count after this operation, or None if unchanged.
        notes: Human-readable annotation for debugging or Writer hints.
    """

    op_type: OpType
    parameters: MappingProxyType[str, Any]
    row_count: int | None
    stitch_count_after: int | None
    notes: str = ""

    def __post_init__(self) -> None:
        # Accept plain dicts at construction sites and promote to MappingProxyType.
        if isinstance(self.parameters, dict):
            object.__setattr__(self, "parameters", MappingProxyType(self.parameters))


@dataclass(frozen=True)
class ComponentIR:
    """
    Complete IR for a single named component.

    Operations are ordered from first to last worked. The Algebraic Checker
    simulates this sequence to verify stitch counts are consistent.

    Attributes:
        component_name: Must match a ``ComponentSpec.name`` in the manifest.
        handedness: LEFT, RIGHT, or NONE — propagated from ComponentSpec.
        operations: Ordered sequence of parameterized operations.
        starting_stitch_count: Live count before the first operation.
        ending_stitch_count: Expected live count after the last operation.
    """

    component_name: str
    handedness: Handedness
    operations: tuple[Operation, ...]
    starting_stitch_count: int
    ending_stitch_count: int

    def __post_init__(self) -> None:
        if self.starting_stitch_count < 0:
            raise ValueError(
                f"starting_stitch_count must be >= 0, got {self.starting_stitch_count}"
            )
        if self.ending_stitch_count < 0:
            raise ValueError(
                f"ending_stitch_count must be >= 0, got {self.ending_stitch_count}"
            )


# Convenience factory functions for the most common single-op components.


def make_cast_on(count: int, notes: str = "") -> Operation:
    """Create a CAST_ON operation for ``count`` stitches."""
    return Operation(
        op_type=OpType.CAST_ON,
        parameters={"count": count},
        row_count=None,
        stitch_count_after=count,
        notes=notes,
    )


def make_work_even(row_count: int, stitch_count: int, notes: str = "") -> Operation:
    """Create a WORK_EVEN operation spanning ``row_count`` rows."""
    return Operation(
        op_type=OpType.WORK_EVEN,
        parameters={},
        row_count=row_count,
        stitch_count_after=stitch_count,
        notes=notes,
    )


def make_bind_off(count: int, notes: str = "") -> Operation:
    """Create a BIND_OFF operation consuming ``count`` stitches."""
    return Operation(
        op_type=OpType.BIND_OFF,
        parameters={"count": count},
        row_count=None,
        stitch_count_after=0,
        notes=notes,
    )
