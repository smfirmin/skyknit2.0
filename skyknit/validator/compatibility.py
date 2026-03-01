"""
Edge-join compatibility validation for the Geometric Validator.

validate_edge_join_compatibility checks every Join in a ShapeManifest against
the topology registry's compatibility table.  For each join, it resolves the
edge types on both sides (via the component spec edges) and queries
``get_compatibility(edge_type_a, edge_type_b, join_type)``.

Results:
  VALID       → no error
  INVALID     → ValidationError with severity "error"
  CONDITIONAL → ValidationError with severity "warning"; the actual condition
                is not evaluated here (deferred to the geometry validator)

Terminal edges (e.g. OPEN) must not appear as the source of a join that
connects to another component — they are flagged as "error".
"""

from __future__ import annotations

from dataclasses import dataclass

from skyknit.schemas.manifest import ShapeManifest
from skyknit.topology.registry import get_registry
from skyknit.topology.types import CompatibilityResult, Edge


@dataclass(frozen=True)
class ValidationError:
    """A single geometric validation failure or warning."""

    join_id: str
    message: str
    severity: str  # "error" | "warning"


def validate_edge_join_compatibility(manifest: ShapeManifest) -> list[ValidationError]:
    """
    Check every join's edge-type combination against the topology registry.

    Parameters
    ----------
    manifest:
        The ShapeManifest to validate.

    Returns
    -------
    A list of ValidationErrors (may be empty if all joins are valid).
    INVALID combinations have severity "error"; CONDITIONAL have "warning".
    """
    registry = get_registry()
    edge_map = _build_edge_map(manifest)
    errors: list[ValidationError] = []

    for join in manifest.joins:
        edge_a = edge_map.get(join.edge_a_ref)
        edge_b = edge_map.get(join.edge_b_ref)

        if edge_a is None:
            errors.append(
                ValidationError(
                    join_id=join.id,
                    message=f"edge_a_ref {join.edge_a_ref!r} does not resolve to a known edge",
                    severity="error",
                )
            )
            continue

        if edge_b is None:
            errors.append(
                ValidationError(
                    join_id=join.id,
                    message=f"edge_b_ref {join.edge_b_ref!r} does not resolve to a known edge",
                    severity="error",
                )
            )
            continue

        # Terminal edges must not be the source of a structural join
        if registry.edge_types[edge_a.edge_type].is_terminal:
            errors.append(
                ValidationError(
                    join_id=join.id,
                    message=(
                        f"edge_a ({join.edge_a_ref}) has terminal type "
                        f"{edge_a.edge_type.value!r} and cannot be a join source"
                    ),
                    severity="error",
                )
            )
            continue

        result = registry.get_compatibility(edge_a.edge_type, edge_b.edge_type, join.join_type)

        match result:
            case CompatibilityResult.VALID:
                pass
            case CompatibilityResult.INVALID:
                errors.append(
                    ValidationError(
                        join_id=join.id,
                        message=(
                            f"incompatible edge-join combination: "
                            f"{edge_a.edge_type.value} + {edge_b.edge_type.value} "
                            f"via {join.join_type.value}"
                        ),
                        severity="error",
                    )
                )
            case CompatibilityResult.CONDITIONAL:
                condition_fn = registry.get_condition_fn(
                    edge_a.edge_type, edge_b.edge_type, join.join_type
                )
                errors.append(
                    ValidationError(
                        join_id=join.id,
                        message=(
                            f"conditional compatibility: "
                            f"{edge_a.edge_type.value} + {edge_b.edge_type.value} "
                            f"via {join.join_type.value} "
                            f"(condition: {condition_fn!r} — evaluation deferred)"
                        ),
                        severity="warning",
                    )
                )

    return errors


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_edge_map(manifest: ShapeManifest) -> dict[str, Edge]:
    """Build a flat ``"component.edge"`` → Edge lookup from the manifest."""
    edge_map: dict[str, Edge] = {}
    for component in manifest.components:
        for edge in component.edges:
            edge_map[f"{component.name}.{edge.name}"] = edge
    return edge_map
