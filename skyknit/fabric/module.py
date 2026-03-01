"""
Fabric Module: gauge, stitch motif, and yarn → ConstraintObject per component.

The Fabric Module takes explicit knitting parameters and produces a
ConstraintObject for each component in a garment.  It runs concurrently
with Planner stage 2 once the component list is available.

DeterministicFabricModule (v1)
-------------------------------
Applies a single gauge / stitch motif / yarn spec uniformly across all
components.  The physical tolerance is derived via
``utilities.tolerance.calculate_tolerance_mm`` using a neutral ease multiplier
(1.0 — ease is applied to dimensions in the Planner, not re-applied here).

Future implementations may assign per-component constraints (e.g., tighter
tolerance for the body, looser for the yoke) or integrate a yarn registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from skyknit.schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.utilities.tolerance import calculate_tolerance_mm
from skyknit.utilities.types import Gauge

# Neutral ease multiplier for v1 — ease is already applied to physical
# dimensions in the Planner; the Fabric Module does not re-apply it.
_NEUTRAL_EASE: float = 1.0


@dataclass(frozen=True)
class FabricInput:
    """Inputs for the Fabric Module.

    Attributes:
        component_names: Names of components that need constraints.
            Typically the ``component_list`` from Planner stage 1.
        gauge: Stitch and row density in stitches/rows per inch.
        stitch_motif: Repeating stitch pattern for the garment.
        yarn_spec: Yarn weight, fiber, and needle size.
        precision: Precision preference controlling the tolerance band width.
    """

    component_names: tuple[str, ...]
    gauge: Gauge
    stitch_motif: StitchMotif
    yarn_spec: YarnSpec
    precision: PrecisionPreference


@dataclass(frozen=True)
class FabricOutput:
    """Output of a Fabric Module.

    Attributes:
        constraints: Mapping of component name to its ConstraintObject.
            Keys match the ``component_names`` in the corresponding FabricInput.
    """

    constraints: dict[str, ConstraintObject]


@runtime_checkable
class FabricModule(Protocol):
    """Protocol that all Fabric Module implementations must satisfy."""

    def produce(self, fabric_input: FabricInput) -> FabricOutput:
        """Produce one ConstraintObject per component."""
        ...


class DeterministicFabricModule:
    """Fabric Module that applies a single gauge/motif/yarn to all components.

    No LLM calls.  Suitable for uniform-gauge garments where all components
    share the same knitting parameters.

    The physical tolerance is derived from gauge + precision preference using
    a neutral ease multiplier (1.0).
    """

    def produce(self, fabric_input: FabricInput) -> FabricOutput:
        """Return one ConstraintObject per component in *fabric_input.component_names*."""
        tolerance_mm = calculate_tolerance_mm(
            gauge=fabric_input.gauge,
            ease_multiplier=_NEUTRAL_EASE,
            precision=fabric_input.precision.to_precision_level(),
        )

        constraint = ConstraintObject(
            gauge=fabric_input.gauge,
            stitch_motif=fabric_input.stitch_motif,
            hard_constraints=(),
            yarn_spec=fabric_input.yarn_spec,
            physical_tolerance_mm=tolerance_mm,
        )

        return FabricOutput(constraints={name: constraint for name in fabric_input.component_names})
