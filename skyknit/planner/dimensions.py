"""
Dimension calculator for the Planner.

Applies DimensionRules from a ComponentBlueprint to produce the physical
dimensions dict for a ComponentSpec.

Result of each rule:
    dimension = measurements[measurement_key] × ratios.get(ratio_key, default_ratio)

When ratio_key is None, the measurement is used directly (default_ratio is ignored).
"""

from __future__ import annotations

from skyknit.schemas.garment import ComponentBlueprint
from skyknit.schemas.proportion import ProportionSpec


def compute_dimensions(
    blueprint: ComponentBlueprint,
    proportion_spec: ProportionSpec,
    measurements: dict[str, float],
) -> dict[str, float]:
    """
    Compute the physical dimensions dict for *blueprint* from measurements and ratios.

    Returns a plain ``dict[str, float]`` ready to pass to ``ComponentSpec``.
    ``ComponentSpec.__post_init__`` converts it to ``MappingProxyType`` automatically.

    Raises ``ValueError`` if a required measurement key is absent.
    """
    result: dict[str, float] = {}
    for rule in blueprint.dimension_rules:
        if rule.measurement_key not in measurements:
            raise ValueError(
                f"Component '{blueprint.name}': required measurement "
                f"'{rule.measurement_key}' is missing from measurements dict."
            )
        base = measurements[rule.measurement_key]
        if rule.ratio_key is None:
            result[rule.dimension_key] = base
        else:
            ratio = float(proportion_spec.ratios.get(rule.ratio_key, rule.default_ratio))
            result[rule.dimension_key] = base * ratio
    return result
