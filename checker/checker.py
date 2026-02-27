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

from .joins import validate_join
from .simulate import CheckerError, ErrorOrigin, extract_edge_counts, simulate_component


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
    manifest_names = {comp.name for comp in manifest.components}

    # Flag extra IRs not referenced by the manifest
    for ir_name in irs:
        if ir_name not in manifest_names:
            all_errors.append(
                CheckerError(
                    component_name=ir_name,
                    operation_index=-1,
                    message=f"IR provided for unknown component '{ir_name}' (not in manifest)",
                    error_type=ErrorOrigin.GEOMETRIC_ORIGIN,
                )
            )

    # Step 1 & 2: Simulate each component and extract edge counts
    for comp_spec in manifest.components:
        ir = irs.get(comp_spec.name)
        if ir is None:
            all_errors.append(
                CheckerError(
                    component_name=comp_spec.name,
                    operation_index=-1,
                    message=f"No IR provided for component '{comp_spec.name}'",
                    error_type=ErrorOrigin.FILLER_ORIGIN,
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
        if not constraints:
            all_errors.append(
                CheckerError(
                    component_name="",
                    operation_index=-1,
                    message="Cannot validate joins: no constraints provided (need gauge/tolerance)",
                    error_type=ErrorOrigin.GEOMETRIC_ORIGIN,
                )
            )
        else:
            # Resolve gauge/tolerance per join from the upstream component's constraint.
            # Falls back to the first available constraint if no specific one is found.
            fallback_constraint = next(iter(constraints.values()))
            for join in manifest.joins:
                comp_name = join.edge_a_ref.split(".")[0]
                join_constraint = constraints.get(comp_name, fallback_constraint)
                error = validate_join(
                    join,
                    all_edge_counts,
                    tolerance_mm=join_constraint.physical_tolerance_mm,
                    gauge=join_constraint.gauge,
                )
                if error is not None:
                    all_errors.append(error)

    return CheckerResult(
        passed=len(all_errors) == 0,
        errors=tuple(all_errors),
    )
