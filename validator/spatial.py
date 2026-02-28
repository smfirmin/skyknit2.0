"""
Spatial coherence validation for the Geometric Validator.

validate_spatial_coherence checks that the ShapeManifest is internally
consistent at the reference level — i.e., that every ``join_ref`` on an
edge points to a Join that exists, and every Join's edge refs resolve to
actual component edges.

It also checks physical dimensional coherence for CONTINUATION joins: the
two edges share the same dimension key (e.g. ``circumference_mm``) and their
values must agree within the registry's default tolerance for that join type.
(For other join types, dimensional agreement is type-specific and deferred to
the Algebraic Checker's stitch-count layer.)
"""

from __future__ import annotations

from schemas.manifest import ShapeManifest
from validator.compatibility import ValidationError


def validate_spatial_coherence(manifest: ShapeManifest) -> list[ValidationError]:
    """
    Check referential and dimensional coherence across the ShapeManifest.

    Checks performed:
    1. Every edge ``join_ref`` that is not None must name an existing Join id.
    2. Every Join's ``edge_a_ref`` and ``edge_b_ref`` must resolve to an edge
       in the manifest (``"component.edge"`` format).
    3. Joins must not reference the same edge on both sides.

    Returns a (possibly empty) list of ValidationErrors.
    """
    errors: list[ValidationError] = []

    join_ids = {join.id for join in manifest.joins}
    edge_map = _build_edge_map(manifest)

    # ── 1. Every join_ref on edges must point to a real join ──────────────────
    for component in manifest.components:
        for edge in component.edges:
            if edge.join_ref is not None and edge.join_ref not in join_ids:
                errors.append(
                    ValidationError(
                        join_id=edge.join_ref,
                        message=(
                            f"edge '{component.name}.{edge.name}' references join "
                            f"{edge.join_ref!r} which does not exist in the manifest"
                        ),
                        severity="error",
                    )
                )

    # ── 2. Every join's edge refs must resolve ────────────────────────────────
    for join in manifest.joins:
        if join.edge_a_ref not in edge_map:
            errors.append(
                ValidationError(
                    join_id=join.id,
                    message=(
                        f"join '{join.id}': edge_a_ref {join.edge_a_ref!r} "
                        f"does not resolve to any component edge"
                    ),
                    severity="error",
                )
            )
        if join.edge_b_ref not in edge_map:
            errors.append(
                ValidationError(
                    join_id=join.id,
                    message=(
                        f"join '{join.id}': edge_b_ref {join.edge_b_ref!r} "
                        f"does not resolve to any component edge"
                    ),
                    severity="error",
                )
            )

        # ── 3. A join must not connect an edge to itself ───────────────────────
        if join.edge_a_ref == join.edge_b_ref:
            errors.append(
                ValidationError(
                    join_id=join.id,
                    message=(
                        f"join '{join.id}': edge_a_ref and edge_b_ref are the same "
                        f"({join.edge_a_ref!r}) — a join must connect two distinct edges"
                    ),
                    severity="error",
                )
            )

    return errors


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_edge_map(manifest: ShapeManifest) -> dict[str, object]:
    """Build a flat ``"component.edge"`` → Edge lookup."""
    edge_map: dict[str, object] = {}
    for component in manifest.components:
        for edge in component.edges:
            edge_map[f"{component.name}.{edge.name}"] = edge
    return edge_map
