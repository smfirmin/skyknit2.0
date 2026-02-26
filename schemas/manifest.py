"""
Shape Manifest schema: the output contract of the Planner.

ComponentSpec describes one geometric primitive (shape type, physical
dimensions, typed edges, handedness). ShapeManifest bundles all components
and the join objects that connect them.

Edge and Join objects are imported directly from topology — the manifest
does not redefine these types.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from topology.types import Edge, Join


class ShapeType(str, Enum):
    """Geometric primitive types for v1 top-down sweater construction."""

    CYLINDER = "CYLINDER"
    TRAPEZOID = "TRAPEZOID"
    RECTANGLE = "RECTANGLE"


class Handedness(str, Enum):
    """Handedness annotation for symmetric component instances."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    NONE = "NONE"


@dataclass(frozen=True)
class ComponentSpec:
    """
    A single geometric component in the shape manifest.

    dimensions: physical measurements in mm, keyed by descriptor
        (e.g. {"circumference_mm": 508.0, "depth_mm": 355.6}).
    edges: tuple of Edge objects (from topology). Ordered; names must
        be unique within a component.
    instantiation_count: 1 for most components; 2 for symmetric pairs
        (sleeves). The Planner emits one spec; the Orchestrator instantiates
        the correct number.
    """

    name: str
    shape_type: ShapeType
    dimensions: dict[str, float]
    edges: tuple[Edge, ...]
    handedness: Handedness
    instantiation_count: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ComponentSpec name must not be empty")
        if self.instantiation_count < 1:
            raise ValueError(f"instantiation_count must be >= 1, got {self.instantiation_count}")
        edge_names = [e.name for e in self.edges]
        if len(edge_names) != len(set(edge_names)):
            raise ValueError(
                f"ComponentSpec '{self.name}': edge names must be unique, got {edge_names}"
            )


@dataclass(frozen=True)
class ShapeManifest:
    """
    Complete shape manifest: all components and the joins connecting them.

    joins: tuple of Join objects (from topology). Each Join references
        edges by "component_name.edge_name" strings.
    """

    components: tuple[ComponentSpec, ...]
    joins: tuple[Join, ...]
