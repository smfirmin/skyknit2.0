"""
ComponentSpec builder for the Planner.

Converts a ComponentBlueprint + computed dimensions into a ComponentSpec
ready for inclusion in a ShapeManifest.
"""

from __future__ import annotations

from skyknit.schemas.garment import ComponentBlueprint
from skyknit.schemas.manifest import ComponentSpec
from skyknit.topology.types import Edge


def build_component_spec(
    blueprint: ComponentBlueprint,
    dimensions: dict[str, float],
) -> ComponentSpec:
    """
    Build a ``ComponentSpec`` from *blueprint* and pre-computed *dimensions*.

    *dimensions* must already be in mm (produced by ``compute_dimensions``).
    ``ComponentSpec.__post_init__`` converts the plain dict to ``MappingProxyType``.
    """
    edges = tuple(
        Edge(
            name=edge_spec.name,
            edge_type=edge_spec.edge_type,
            join_ref=edge_spec.join_id,
            dimension_key=edge_spec.dimension_key,
        )
        for edge_spec in blueprint.edges
    )
    return ComponentSpec(
        name=blueprint.name,
        shape_type=blueprint.shape_type,
        dimensions=dimensions,  # type: ignore[arg-type]  # __post_init__ promotes to MappingProxyType
        edges=edges,
        handedness=blueprint.handedness,
        instantiation_count=1,
    )
