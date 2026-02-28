"""
Full Algebraic Checker pipeline.

check_all orchestrates:
  1. Intra-component simulation (simulate_component) for every ComponentIR.
  2. Edge stitch count extraction (extract_edge_counts) to build the flat
     "component.edge" → stitch count table.
  3. Inter-component join validation (validate_all_joins) against that table.

All errors are collected (not short-circuited) and returned in CheckerResult.

For join validation the tighter (smaller) physical_tolerance_mm of the two
joined components is used.  If a component has no ConstraintObject the global
default of 10mm is applied.
"""

from __future__ import annotations

from dataclasses import dataclass

from checker.joins import validate_join
from checker.simulate import CheckerError, extract_edge_counts, simulate_component
from schemas.constraint import ConstraintObject
from schemas.ir import ComponentIR
from schemas.manifest import ShapeManifest

_DEFAULT_TOLERANCE_MM = 10.0


@dataclass(frozen=True)
class CheckerResult:
    """Top-level outcome of running the full Algebraic Checker pipeline."""

    passed: bool
    errors: tuple[CheckerError, ...]


def check_all(
    manifest: ShapeManifest,
    irs: dict[str, ComponentIR],
    constraints: dict[str, ConstraintObject],
) -> CheckerResult:
    """
    Run the complete Algebraic Checker over all components and joins.

    Parameters
    ----------
    manifest:
        The ShapeManifest describing every component and their joins.
    irs:
        Mapping of component name → ComponentIR (one per manifest component).
    constraints:
        Mapping of component name → ConstraintObject.  Components not present
        in this dict fall back to ``_DEFAULT_TOLERANCE_MM`` and whatever gauge
        is available from a sibling component.

    Returns
    -------
    CheckerResult with ``passed=True`` and an empty errors tuple when every
    component simulation and every join is valid.
    """
    all_errors: list[CheckerError] = []
    all_edge_counts: dict[str, int] = {}

    # ── 1. Intra-component simulation + edge extraction ───────────────────────
    for component_spec in manifest.components:
        name = component_spec.name
        ir = irs.get(name)
        if ir is None:
            all_errors.append(
                CheckerError(
                    component_name=name,
                    operation_index=-1,
                    message=f"no ComponentIR provided for component {name!r}",
                    error_type="geometric_origin",
                )
            )
            continue

        sim = simulate_component(ir)
        all_errors.extend(sim.errors)

        edge_counts = extract_edge_counts(ir, component_spec)
        for edge_name, count in edge_counts.items():
            all_edge_counts[f"{name}.{edge_name}"] = count

    # ── 2. Inter-component join validation ────────────────────────────────────
    for join in manifest.joins:
        # Choose the tighter tolerance of the two joined components
        tolerance_mm = _join_tolerance(join.edge_a_ref, join.edge_b_ref, constraints)
        # Use gauge from whichever component we can find
        gauge = _join_gauge(join.edge_a_ref, join.edge_b_ref, constraints)
        if gauge is None:
            all_errors.append(
                CheckerError(
                    component_name=join.id,
                    operation_index=-1,
                    message=f"no gauge available for join '{join.id}' — skipping",
                    error_type="geometric_origin",
                )
            )
            continue
        error = validate_join(join, all_edge_counts, tolerance_mm, gauge)
        if error is not None:
            all_errors.append(error)

    return CheckerResult(
        passed=len(all_errors) == 0,
        errors=tuple(all_errors),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _component_name_from_ref(edge_ref: str) -> str:
    """Extract component name from a 'component.edge' reference string."""
    return edge_ref.split(".")[0]


def _join_tolerance(
    edge_a_ref: str,
    edge_b_ref: str,
    constraints: dict[str, ConstraintObject],
) -> float:
    name_a = _component_name_from_ref(edge_a_ref)
    name_b = _component_name_from_ref(edge_b_ref)
    tol_a = (
        constraints[name_a].physical_tolerance_mm
        if name_a in constraints
        else _DEFAULT_TOLERANCE_MM
    )
    tol_b = (
        constraints[name_b].physical_tolerance_mm
        if name_b in constraints
        else _DEFAULT_TOLERANCE_MM
    )
    return min(tol_a, tol_b)


def _join_gauge(
    edge_a_ref: str,
    edge_b_ref: str,
    constraints: dict[str, ConstraintObject],
):  # type: ignore[return]
    """Return gauge from either joined component, preferring edge_a."""
    name_a = _component_name_from_ref(edge_a_ref)
    name_b = _component_name_from_ref(edge_b_ref)
    if name_a in constraints:
        return constraints[name_a].gauge
    if name_b in constraints:
        return constraints[name_b].gauge
    return None
