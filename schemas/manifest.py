"""
Shape manifest schema: component specifications and join topology.

ComponentSpec describes a single named shape with physical dimensions and
edge references. ShapeManifest is the complete structural description of a
sweater: all components and all joins connecting their edges.

Edge and Join objects are reused from topology — schemas does not redefine them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from topology.types import Edge, Join


class ShapeType(str, Enum):
    """Geometric primitive for a knitted component."""

    CYLINDER = "CYLINDER"
    TRAPEZOID = "TRAPEZOID"
    RECTANGLE = "RECTANGLE"


class Handedness(str, Enum):
    """Directional orientation of a component (for mirrored pairs)."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    NONE = "NONE"


@dataclass(frozen=True)
class ComponentSpec:
    """
    Specification for a single named component of the sweater.

    Attributes:
        name: Unique component identifier (e.g. "body", "left_sleeve").
        shape_type: Geometric primitive this component is based on.
        dimensions: Physical dimensions in mm keyed by measurement name.
        edges: Ordered tuple of typed edges bounding this component.
        handedness: LEFT, RIGHT, or NONE for unpaired components.
        instantiation_count: How many times this spec is instantiated (e.g. 2 for sleeves).
    """

    name: str
    shape_type: ShapeType
    dimensions: MappingProxyType[str, float]
    edges: tuple[Edge, ...]
    handedness: Handedness
    instantiation_count: int

    def __post_init__(self) -> None:
        if isinstance(self.dimensions, dict):
            object.__setattr__(self, "dimensions", MappingProxyType(self.dimensions))
        if self.instantiation_count < 1:
            raise ValueError(
                f"instantiation_count must be >= 1, got {self.instantiation_count}"
            )


@dataclass(frozen=True)
class ShapeManifest:
    """
    Complete structural topology of the sweater.

    Attributes:
        components: All component specs.
        joins: All joins connecting component edges.
    """

    components: tuple[ComponentSpec, ...]
    joins: tuple[Join, ...]
