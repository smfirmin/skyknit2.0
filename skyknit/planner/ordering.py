"""
Component construction ordering derived from the join dependency graph.

The join graph encodes the construction sequence formally: for each directional
join, the ``edge_a_ref`` component is upstream (worked first) and the
``edge_b_ref`` component is downstream (worked after).  SEAM joins are symmetric
and impose no ordering constraint.

``derive_component_order`` performs a topological sort (Kahn's algorithm) on
this DAG and returns component names in a valid construction sequence.  When
multiple components have no remaining dependencies (a "tier"), the original
component tuple order from the ShapeManifest is preserved as a tiebreaker.
"""

from __future__ import annotations

from skyknit.schemas.manifest import ShapeManifest
from skyknit.topology.types import JoinType


def derive_component_order(manifest: ShapeManifest) -> list[str]:
    """Return component names in topological (construction) order.

    Derived from the join dependency graph:

    - Directional joins (all except SEAM): the ``edge_a_ref`` component is
      upstream and must be worked before the ``edge_b_ref`` component.
    - SEAM joins are symmetric; they impose no ordering constraint.

    Within each dependency tier, the original component tuple order from
    *manifest* is preserved as the tiebreaker.

    Parameters
    ----------
    manifest:
        The ShapeManifest whose join graph determines the construction order.

    Returns
    -------
    list[str]
        Component names in a valid topological order.

    Raises
    ------
    ValueError
        If the join graph contains a cycle (topologically impossible for a valid
        garment but checked defensively).
    """
    component_names = [c.name for c in manifest.components]
    name_index: dict[str, int] = {name: i for i, name in enumerate(component_names)}

    # Build dependency sets: deps[name] = set of names that must precede it.
    deps: dict[str, set[str]] = {name: set() for name in component_names}

    for join in manifest.joins:
        # SEAM is symmetric — neither side depends on the other.
        if join.join_type == JoinType.SEAM:
            continue

        upstream = join.edge_a_ref.split(".")[0]
        downstream = join.edge_b_ref.split(".")[0]

        if upstream == downstream:
            continue  # self-referential join edge (unusual; skip)

        if upstream in deps and downstream in deps:
            deps[downstream].add(upstream)

    # Kahn's algorithm: repeatedly pick the lowest-index available node.
    result: list[str] = []
    remaining: dict[str, set[str]] = {name: set(d) for name, d in deps.items()}
    in_result: set[str] = set()

    while len(result) < len(component_names):
        # Available = no remaining dependencies and not yet placed.
        available = sorted(
            (name for name in component_names if name not in in_result and not remaining[name]),
            key=lambda n: name_index[n],
        )

        if not available:
            cycle_members = [name for name in component_names if name not in in_result]
            raise ValueError(
                f"Cycle detected in join dependency graph among components: {cycle_members}"
            )

        node = available[0]
        result.append(node)
        in_result.add(node)

        # Remove node from all remaining dependency sets.
        for dep_set in remaining.values():
            dep_set.discard(node)

    return result
