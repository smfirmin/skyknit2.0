"""
Algebraic Checker: full pipeline for validating a complete sweater pattern.

Orchestrates intra-component simulation and inter-component join validation.
Errors are classified as filler-origin (stitch count problems within a
component) or geometric-origin (join topology problems between components).
"""

from __future__ import annotations

from dataclasses import dataclass

from schemas.constraint import ConstraintObject
from schemas.ir import ComponentIR
from schemas.manifest import ShapeManifest

from .joins import validate_all_joins
from .simulate import CheckerError, extract_edge_counts, simulate_component


@dataclass(frozen=True)
class CheckerResult:
    """
    Aggregate result from the full algebraic checking pipeline.

    Attributes:
        passed: True if all components simulate correctly and all joins validate.
        errors: Combined list of all errors found (filler-origin and geometric-origin).
    """

    passed: bool
    errors: tuple[CheckerError, ...]


def check_all(
    manifest: ShapeManifest,
    irs: dict[str, ComponentIR],
    constraints: dict[str, ConstraintObject],
) -> CheckerResult:
    """
    Run the full algebraic checking pipeline.

    1. Simulate each component IR (intra-component validation)
    2. Extract edge stitch counts from successful simulations
    3. Validate all joins against extracted edge counts (inter-component validation)
    4. Return aggregate result with classified errors

    Args:
        manifest: The sweater's structural topology.
        irs: Component IRs keyed by component name.
        constraints: Constraint objects keyed by component name.
    """
    all_errors: list[CheckerError] = []
    all_edge_counts: dict[str, int] = {}

    # Step 1 & 2: Simulate each component and extract edge counts
    for comp_spec in manifest.components:
        ir = irs.get(comp_spec.name)
        if ir is None:
            all_errors.append(
                CheckerError(
                    component_name=comp_spec.name,
                    operation_index=-1,
                    message=f"No IR provided for component '{comp_spec.name}'",
                    error_type="filler_origin",
                )
            )
            continue

        sim_result = simulate_component(ir)
        all_errors.extend(sim_result.errors)

        # Extract edge counts even if simulation had errors, to catch as many
        # join problems as possible in a single pass
        edge_counts = extract_edge_counts(ir, comp_spec)
        all_edge_counts.update(edge_counts)

    # Step 3: Validate inter-component joins
    if manifest.joins:
        # Use the first available constraint for gauge/tolerance.
        # In practice all components in a garment share the same gauge.
        first_constraint = next(iter(constraints.values())) if constraints else None
        if first_constraint is not None:
            join_errors = validate_all_joins(
                manifest.joins,
                all_edge_counts,
                tolerance_mm=first_constraint.physical_tolerance_mm,
                gauge=first_constraint.gauge,
            )
            all_errors.extend(join_errors)

    return CheckerResult(
        passed=len(all_errors) == 0,
        errors=tuple(all_errors),
    )
