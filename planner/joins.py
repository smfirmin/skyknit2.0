"""
Join builder for the Planner.

Converts JoinSpec objects into topology Join objects, populating parameters
from the topology registry defaults table.
"""

from __future__ import annotations

from schemas.garment import JoinSpec
from schemas.manifest import ComponentSpec
from topology.registry import get_registry
from topology.types import Edge, Join


def _resolve_edge(edge_ref: str, component_specs: dict[str, ComponentSpec]) -> Edge:
    """
    Look up an Edge by its ``"component_name.edge_name"`` ref string.

    Raises ``ValueError`` if the component or edge name cannot be resolved.
    """
    parts = edge_ref.split(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Edge ref '{edge_ref}' must be in 'component_name.edge_name' format.")
    component_name, edge_name = parts
    if component_name not in component_specs:
        raise ValueError(
            f"Edge ref '{edge_ref}': component '{component_name}' not found in component specs."
        )
    spec = component_specs[component_name]
    matching = [e for e in spec.edges if e.name == edge_name]
    if not matching:
        raise ValueError(
            f"Edge ref '{edge_ref}': edge '{edge_name}' not found on component '{component_name}'."
        )
    return matching[0]


def build_join(
    join_spec: JoinSpec,
    component_specs: dict[str, ComponentSpec],
) -> Join:
    """
    Build a ``Join`` from *join_spec*, populating parameters from the registry defaults.

    The topology registry's defaults table is keyed by
    ``(edge_type_a, edge_type_b, join_type)``; the returned dict is used as
    the join's ``parameters``.  For join types with no defaults (e.g.
    CONTINUATION, HELD_STITCH) this resolves to an empty dict.

    Raises ``ValueError`` if either edge ref cannot be resolved.
    """
    edge_a = _resolve_edge(join_spec.edge_a_ref, component_specs)
    edge_b = _resolve_edge(join_spec.edge_b_ref, component_specs)

    defaults = get_registry().get_defaults(
        edge_a.edge_type,
        edge_b.edge_type,
        join_spec.join_type,
    )

    return Join(
        id=join_spec.id,
        join_type=join_spec.join_type,
        edge_a_ref=join_spec.edge_a_ref,
        edge_b_ref=join_spec.edge_b_ref,
        parameters=defaults,  # Join.__post_init__ promotes dict → MappingProxyType
    )


def build_all_joins(
    join_specs: tuple[JoinSpec, ...],
    component_specs: dict[str, ComponentSpec],
) -> list[Join]:
    """Build all joins for the garment from *join_specs*."""
    return [build_join(js, component_specs) for js in join_specs]
