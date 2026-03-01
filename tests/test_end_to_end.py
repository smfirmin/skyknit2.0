"""
End-to-end integration tests for the full Skyknit pipeline.

Exercises: garment registry → Orchestrator → TemplateWriter for both
canonical garment types, verifying that the complete pipeline produces
valid, checked pattern output containing expected prose markers.
"""

from __future__ import annotations

from types import MappingProxyType

import skyknit.planner.garments  # noqa: F401 — triggers registration of built-in factories
import skyknit.planner.garments.registry as garment_registry
from skyknit.fabric.module import FabricInput
from skyknit.orchestrator.pipeline import DeterministicOrchestrator, OrchestratorInput
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec
from skyknit.utilities.types import Gauge
from skyknit.writer.writer import TemplateWriter, WriterInput

# ── Shared test fixtures ───────────────────────────────────────────────────────

_GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)

_PROPORTION = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
    precision=PrecisionPreference.MEDIUM,
)

_FABRIC = FabricInput(
    component_names=(),  # overridden by Orchestrator from component_order
    gauge=_GAUGE,
    stitch_motif=StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1),
    yarn_spec=YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0),
    precision=PrecisionPreference.MEDIUM,
)

_MEASUREMENTS_DROP = {
    "chest_circumference_mm": 914.4,
    "body_length_mm": 457.2,
    "sleeve_length_mm": 495.3,
    "upper_arm_circumference_mm": 381.0,
    "wrist_circumference_mm": 152.4,
}

_MEASUREMENTS_YOKE = {**_MEASUREMENTS_DROP, "yoke_depth_mm": 228.6}


# ── Drop-shoulder pullover ─────────────────────────────────────────────────────


def test_drop_shoulder_full_pipeline():
    spec = garment_registry.get("top-down-drop-shoulder-pullover")
    oi = OrchestratorInput(
        garment_spec=spec,
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_DROP,
        fabric_input=_FABRIC,
    )
    output = DeterministicOrchestrator().run(oi)

    assert output.checker_result.passed
    assert output.component_order.index("body") < output.component_order.index("left_sleeve")
    assert output.component_order.index("body") < output.component_order.index("right_sleeve")

    wi = WriterInput(
        manifest=output.manifest,
        irs=output.irs,
        component_order=output.component_order,
    )
    wo = TemplateWriter().write(wi)

    assert "Cast on" in wo.full_pattern
    assert "Pick up" in wo.full_pattern
    assert "Bind off" in wo.full_pattern
    assert len(wo.sections) == 3


def test_drop_shoulder_pattern_has_three_named_sections():
    spec = garment_registry.get("top-down-drop-shoulder-pullover")
    oi = OrchestratorInput(
        garment_spec=spec,
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_DROP,
        fabric_input=_FABRIC,
    )
    output = DeterministicOrchestrator().run(oi)
    wi = WriterInput(
        manifest=output.manifest,
        irs=output.irs,
        component_order=output.component_order,
    )
    wo = TemplateWriter().write(wi)
    assert "Body" in wo.full_pattern
    assert "Left Sleeve" in wo.full_pattern
    assert "Right Sleeve" in wo.full_pattern


# ── Yoke pullover ─────────────────────────────────────────────────────────────


def test_yoke_pullover_full_pipeline():
    spec = garment_registry.get("top-down-yoke-pullover")
    oi = OrchestratorInput(
        garment_spec=spec,
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_YOKE,
        fabric_input=_FABRIC,
    )
    output = DeterministicOrchestrator().run(oi)

    assert output.checker_result.passed
    assert output.component_order.index("yoke") < output.component_order.index("body")

    wi = WriterInput(
        manifest=output.manifest,
        irs=output.irs,
        component_order=output.component_order,
    )
    wo = TemplateWriter().write(wi)

    assert "Work even" in wo.full_pattern
    assert "Bind off" in wo.full_pattern
    assert len(wo.sections) == 4


def test_yoke_pullover_pattern_has_four_named_sections():
    spec = garment_registry.get("top-down-yoke-pullover")
    oi = OrchestratorInput(
        garment_spec=spec,
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_YOKE,
        fabric_input=_FABRIC,
    )
    output = DeterministicOrchestrator().run(oi)
    wi = WriterInput(
        manifest=output.manifest,
        irs=output.irs,
        component_order=output.component_order,
    )
    wo = TemplateWriter().write(wi)
    assert "Yoke" in wo.full_pattern
    assert "Body" in wo.full_pattern
    assert "Left Sleeve" in wo.full_pattern
    assert "Right Sleeve" in wo.full_pattern


# ── Garment registry ──────────────────────────────────────────────────────────


def test_both_garment_types_registered():
    types = garment_registry.list_types()
    assert "top-down-drop-shoulder-pullover" in types
    assert "top-down-yoke-pullover" in types
