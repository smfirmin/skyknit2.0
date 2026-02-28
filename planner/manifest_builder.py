"""
Shape manifest builder for the Planner.

Orchestrates the full pipeline:
  GarmentSpec + ProportionSpec + measurements
    → ComponentSpec objects (via dimensions + component_specs tools)
    → Join objects (via joins tool, using topology registry defaults)
    → ShapeManifest

Validation (validate_phase1) is the caller's responsibility — not called here.
"""

from __future__ import annotations

from planner.component_specs import build_component_spec
from planner.dimensions import compute_dimensions
from planner.joins import build_all_joins
from schemas.garment import GarmentSpec
from schemas.manifest import ShapeManifest
from schemas.proportion import ProportionSpec


def build_shape_manifest(
    garment_spec: GarmentSpec,
    proportion_spec: ProportionSpec,
    measurements: dict[str, float],
) -> ShapeManifest:
    """
    Build a ``ShapeManifest`` from the garment blueprint, ease ratios, and body measurements.

    Steps:
      1. Validate that all required measurement keys are present (fail-fast).
      2. For each ``ComponentBlueprint``: compute dimensions, then build a ``ComponentSpec``.
      3. Build all ``Join`` objects using topology registry defaults.
      4. Assemble and return ``ShapeManifest``.

    Raises ``ValueError`` if any required measurement key is absent.
    """
    # Step 1 — validate required measurements
    missing = garment_spec.required_measurements - measurements.keys()
    if missing:
        raise ValueError(
            f"Missing required measurements for '{garment_spec.garment_type}': {sorted(missing)}"
        )

    # Step 2 — build ComponentSpecs
    component_specs_list = []
    for blueprint in garment_spec.components:
        dims = compute_dimensions(blueprint, proportion_spec, measurements)
        spec = build_component_spec(blueprint, dims)
        component_specs_list.append(spec)

    component_specs_by_name = {spec.name: spec for spec in component_specs_list}

    # Step 3 — build Joins
    joins = build_all_joins(garment_spec.joins, component_specs_by_name)

    return ShapeManifest(
        components=tuple(component_specs_list),
        joins=tuple(joins),
    )
