"""
Public made-to-measure pattern generation API.

generate_pattern() is the single entry point that takes body measurements,
yarn specification, and design preferences and returns complete pattern prose.
It wires the full pipeline: garment registry → Design Module → Fabric Module
→ Orchestrator → Writer.
"""

from __future__ import annotations

import skyknit.planner.garments  # noqa: F401 — ensures all garment factories are registered
import skyknit.planner.garments.registry as garment_registry
from skyknit.design.module import DesignInput, DeterministicDesignModule, EaseLevel
from skyknit.fabric.module import FabricInput
from skyknit.orchestrator.pipeline import DeterministicOrchestrator, OrchestratorInput
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.utilities.types import Gauge
from skyknit.writer.writer import TemplateWriter, WriterInput


def generate_pattern(
    garment_type: str,
    measurements: dict[str, float],
    gauge: Gauge,
    stitch_motif: StitchMotif,
    yarn_spec: YarnSpec,
    ease_level: EaseLevel = EaseLevel.STANDARD,
    precision: PrecisionPreference = PrecisionPreference.MEDIUM,
) -> str:
    """
    Generate a complete knitting pattern from body measurements and yarn specification.

    Parameters
    ----------
    garment_type:
        Registry key for the garment to generate (e.g.
        ``"top-down-drop-shoulder-pullover"`` or ``"top-down-yoke-pullover"``).
    measurements:
        Body measurements in millimetres.  Required keys depend on the garment
        type; see the relevant GarmentSpec for details.
    gauge:
        Knitting gauge — stitches per inch and rows per inch.
    stitch_motif:
        Stitch pattern (e.g. stockinette, 2×2 rib) with repeat constraints.
    yarn_spec:
        Yarn weight, fibre, and needle size.
    ease_level:
        Desired ease level; defaults to STANDARD.
    precision:
        Tolerance precision; defaults to MEDIUM.

    Returns
    -------
    str
        Full pattern prose ready to hand to a knitter, with one section per
        garment component in construction order.

    Raises
    ------
    KeyError
        If *garment_type* is not registered in the garment registry.
    PipelineError
        If the pipeline fails to produce a valid pattern (planner, validator,
        filler, or checker stage failure).
    """
    spec = garment_registry.get(garment_type)

    design_out = DeterministicDesignModule().design(
        DesignInput(
            garment_type=garment_type,
            ease_level=ease_level,
            precision=precision,
        )
    )

    fabric_in = FabricInput(
        component_names=tuple(c.name for c in spec.components),
        gauge=gauge,
        stitch_motif=stitch_motif,
        yarn_spec=yarn_spec,
        precision=precision,
    )

    orch_out = DeterministicOrchestrator().run(
        OrchestratorInput(
            garment_spec=spec,
            proportion_spec=design_out.proportion_spec,
            measurements=measurements,
            fabric_input=fabric_in,
        )
    )

    writer_out = TemplateWriter().write(
        WriterInput(
            manifest=orch_out.manifest,
            irs=orch_out.irs,
            component_order=orch_out.component_order,
        )
    )

    return writer_out.full_pattern
