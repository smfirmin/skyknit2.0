"""
GarmentSpec schema — topology and dimension-rule blueprint for a garment type.

Produced by the Design Module (LLM) or a canonical factory; consumed by the Planner.
Carries zero stitch awareness — all dimensions are physical (mm).

Key types:
  EdgeSpec          — one edge blueprint (name, edge_type, join_id, dimension_key)
  DimensionRule     — formula: measurements[measurement_key] × ratios[ratio_key]
  ComponentBlueprint — full spec for one component
  JoinSpec          — one join in the topology
  GarmentSpec       — complete garment blueprint (components + joins + required measurements)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from skyknit.schemas.manifest import Handedness, ShapeType
from skyknit.topology.types import EdgeType, JoinType


@dataclass(frozen=True)
class EdgeSpec:
    """Blueprint for one named edge of a component."""

    name: str
    edge_type: EdgeType
    join_id: str | None = None  # None for terminal edges (no Join connection)
    dimension_key: str | None = None  # explicit resolver routing; None = positional fallback


@dataclass(frozen=True)
class DimensionRule:
    """
    Rule for computing one physical dimension of a component.

    Result = measurements[measurement_key] × ratios.get(ratio_key, default_ratio)

    When ratio_key is None the measurement is used directly (no ease applied).
    """

    dimension_key: str  # key written into ComponentSpec.dimensions
    measurement_key: str  # key read from measurements dict
    ratio_key: str | None = None  # key read from ProportionSpec.ratios; None = direct measurement
    default_ratio: float = field(default=1.0)  # fallback when ratio_key is absent from ratios


@dataclass(frozen=True)
class ComponentBlueprint:
    """Full blueprint for one garment component: shape, edges, and dimension rules."""

    name: str
    shape_type: ShapeType
    handedness: Handedness
    edges: tuple[EdgeSpec, ...]
    dimension_rules: tuple[DimensionRule, ...]


@dataclass(frozen=True)
class JoinSpec:
    """Blueprint for one join in the garment topology."""

    id: str
    join_type: JoinType
    edge_a_ref: str  # "component_name.edge_name" (upstream / source)
    edge_b_ref: str  # "component_name.edge_name" (downstream / receiving)


@dataclass(frozen=True)
class GarmentSpec:
    """
    Complete topology and dimension-rule specification for a garment type.

    The Planner consumes this to produce a ShapeManifest.  No stitch awareness;
    all dimensions are physical units (mm).

    Attributes:
        garment_type: Descriptive label, e.g. ``"top-down-yoke-pullover"``.
        components: Ordered blueprints (construction sequence).
        joins: All joins in the garment topology.
        required_measurements: Keys that must be present in the measurements dict
            passed to the Planner.  Validated fail-fast before planning begins.
    """

    garment_type: str
    components: tuple[ComponentBlueprint, ...]
    joins: tuple[JoinSpec, ...]
    required_measurements: frozenset[str]
