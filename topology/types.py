"""
Core type definitions for the knitting topology layer.

Enums are the canonical vocabulary; dataclasses are the runtime objects.
Registry entry types (EdgeTypeEntry, JoinTypeEntry, etc.) are loaded from
the YAML lookup tables and are frozen after startup — never written to at
runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Enums ──────────────────────────────────────────────────────────────────────


class EdgeType(str, Enum):
    """Physical boundary types for component shapes."""

    CAST_ON = "CAST_ON"
    LIVE_STITCH = "LIVE_STITCH"
    BOUND_OFF = "BOUND_OFF"
    PICKUP = "PICKUP"
    OPEN = "OPEN"


class JoinType(str, Enum):
    """Connection types between pairs of component edges."""

    CONTINUATION = "CONTINUATION"
    HELD_STITCH = "HELD_STITCH"
    CAST_ON_JOIN = "CAST_ON_JOIN"
    PICKUP = "PICKUP"
    SEAM = "SEAM"


class CompatibilityResult(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    CONDITIONAL = "CONDITIONAL"


class ArithmeticImplication(str, Enum):
    """How a join type affects the active stitch count at its boundary."""

    ONE_TO_ONE = "ONE_TO_ONE"   # count carries over unchanged
    ADDITIVE = "ADDITIVE"       # new stitches introduced (cast_on_count)
    RATIO = "RATIO"             # count derived from source length × pickup_ratio
    STRUCTURAL = "STRUCTURAL"   # two stitch sets consumed and merged


class RenderingMode(str, Enum):
    INLINE = "inline"
    INSTRUCTION = "instruction"
    HEADER_NOTE = "header_note"


# ── Registry entry types (frozen, loaded from YAML) ───────────────────────────


@dataclass(frozen=True)
class EdgeTypeEntry:
    id: EdgeType
    description: str
    has_live_stitches: bool
    is_terminal: bool
    phase_constraint: str
    notes: str = ""


@dataclass(frozen=True)
class JoinTypeEntry:
    id: JoinType
    description: str
    symmetric: bool
    directional: bool
    owns_parameters: tuple[str, ...]
    construction_methods: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class CompatibilityEntry:
    edge_type_a: EdgeType
    edge_type_b: EdgeType
    join_type: JoinType
    result: CompatibilityResult
    condition_fn: Optional[str] = None  # only set when result is CONDITIONAL


@dataclass(frozen=True)
class ArithmeticEntry:
    join_type: JoinType
    implication: ArithmeticImplication
    notes: str = ""


@dataclass(frozen=True)
class WriterDispatchEntry:
    join_type: JoinType
    rendering_mode: RenderingMode
    template_key: str
    directionality_note: bool
    conditional_template_key: Optional[str] = None  # used when compatibility result is CONDITIONAL
    notes: str = ""


# ── Runtime objects ────────────────────────────────────────────────────────────


@dataclass
class Edge:
    """A typed boundary of a component shape."""

    name: str
    edge_type: EdgeType
    join_ref: Optional[str] = None  # ID of the Join object; None for OPEN edges


@dataclass
class Join:
    """
    First-class connection between exactly two component edges.

    edge_a_ref and edge_b_ref are "component_name.edge_name" strings.
    The key is ordered: edge_a is from the upstream/source component,
    edge_b is from the downstream/receiving component — matching the
    ordering convention in the Compatibility Table.
    """

    id: str
    join_type: JoinType
    edge_a_ref: str                              # "component_name.edge_name"
    edge_b_ref: str                              # "component_name.edge_name"
    parameters: dict = field(default_factory=dict)  # join-owned parameters
