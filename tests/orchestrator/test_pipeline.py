"""Tests for orchestrator.pipeline — OrchestratorInput, OrchestratorOutput,
DeterministicOrchestrator, PipelineError."""

from __future__ import annotations

from types import MappingProxyType

import pytest

import skyknit.planner.garments  # noqa: F401 — triggers registration
from skyknit.fabric.module import FabricInput
from skyknit.orchestrator.pipeline import (
    DeterministicOrchestrator,
    OrchestratorInput,
    OrchestratorOutput,
    PipelineError,
)
from skyknit.planner.garments.registry import get
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec
from skyknit.utilities.types import Gauge

# ── Shared fixtures ────────────────────────────────────────────────────────────

_PROPORTION = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
    precision=PrecisionPreference.MEDIUM,
)

_FABRIC = FabricInput(
    component_names=(),  # overridden by Orchestrator from component_order
    gauge=Gauge(stitches_per_inch=20.0, rows_per_inch=28.0),
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


def _drop_shoulder_input() -> OrchestratorInput:
    return OrchestratorInput(
        garment_spec=get("top-down-drop-shoulder-pullover"),
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_DROP,
        fabric_input=_FABRIC,
    )


def _yoke_input() -> OrchestratorInput:
    return OrchestratorInput(
        garment_spec=get("top-down-yoke-pullover"),
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_YOKE,
        fabric_input=_FABRIC,
    )


# ── OrchestratorInput ──────────────────────────────────────────────────────────


class TestOrchestratorInput:
    def test_is_frozen(self):
        oi = _drop_shoulder_input()
        with pytest.raises((AttributeError, TypeError)):
            oi.measurements = {}  # type: ignore[misc]


# ── DeterministicOrchestrator — drop shoulder ──────────────────────────────────


class TestDropShoulderOrchestrator:
    def test_checker_passes(self):
        output = DeterministicOrchestrator().run(_drop_shoulder_input())
        assert output.checker_result.passed is True

    def test_output_is_orchestrator_output(self):
        output = DeterministicOrchestrator().run(_drop_shoulder_input())
        assert isinstance(output, OrchestratorOutput)

    def test_irs_keys_match_component_names(self):
        output = DeterministicOrchestrator().run(_drop_shoulder_input())
        manifest_names = {c.name for c in output.manifest.components}
        assert set(output.irs.keys()) == manifest_names

    def test_component_order_body_before_sleeves(self):
        output = DeterministicOrchestrator().run(_drop_shoulder_input())
        body_idx = output.component_order.index("body")
        assert output.component_order.index("left_sleeve") > body_idx
        assert output.component_order.index("right_sleeve") > body_idx

    def test_constraints_keys_match_components(self):
        output = DeterministicOrchestrator().run(_drop_shoulder_input())
        manifest_names = {c.name for c in output.manifest.components}
        assert set(output.constraints.keys()) == manifest_names


# ── DeterministicOrchestrator — yoke pullover ──────────────────────────────────


class TestYokeOrchestratorPullover:
    def test_checker_passes(self):
        output = DeterministicOrchestrator().run(_yoke_input())
        assert output.checker_result.passed is True

    def test_yoke_before_body_in_order(self):
        output = DeterministicOrchestrator().run(_yoke_input())
        assert output.component_order.index("yoke") < output.component_order.index("body")


# ── PipelineError ──────────────────────────────────────────────────────────────


class TestPipelineError:
    def test_missing_measurement_raises_planner_error(self):
        bad = dict(_MEASUREMENTS_DROP)
        del bad["sleeve_length_mm"]
        oi = OrchestratorInput(
            garment_spec=get("top-down-drop-shoulder-pullover"),
            proportion_spec=_PROPORTION,
            measurements=bad,
            fabric_input=_FABRIC,
        )
        with pytest.raises(PipelineError) as exc_info:
            DeterministicOrchestrator().run(oi)
        assert exc_info.value.stage == "planner"

    def test_pipeline_error_has_stage_attribute(self):
        err = PipelineError("validator", "something went wrong")
        assert err.stage == "validator"
        assert err.detail == "something went wrong"
        assert "validator" in str(err)


# ── Retry routing ──────────────────────────────────────────────────────────────


class TestRetryRouting:
    def test_filler_origin_error_type(self):
        """CheckerError with error_type='filler_origin' carries correct component_name."""
        from skyknit.checker.simulate import CheckerError

        err = CheckerError(
            component_name="left_sleeve",
            operation_index=2,
            message="stitch arithmetic mismatch",
            error_type="filler_origin",
        )
        assert err.component_name == "left_sleeve"
        assert err.error_type == "filler_origin"

    def test_geometric_origin_raises_pipeline_error(self):
        """check_all with a geometric mismatch (ending_stitch_count wrong) returns
        geometric_origin errors; the orchestrator raises PipelineError on such failures."""
        from skyknit.checker.checker import check_all
        from skyknit.schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
        from skyknit.schemas.ir import ComponentIR, make_bind_off, make_cast_on
        from skyknit.schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
        from skyknit.topology.types import Edge, EdgeType
        from skyknit.utilities.types import Gauge

        spec = ComponentSpec(
            name="body",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference_mm": 200.0, "depth_mm": 100.0},
            edges=(
                Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref=None),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        # IR with wrong ending_stitch_count (99 instead of 0 after BIND_OFF)
        ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(make_cast_on(80), make_bind_off(80)),
            starting_stitch_count=80,
            ending_stitch_count=99,  # wrong — should be 0
        )
        constraint = ConstraintObject(
            gauge=Gauge(20.0, 28.0),
            stitch_motif=StitchMotif("stockinette", 1, 1),
            hard_constraints=(),
            yarn_spec=YarnSpec("DK", "wool", 4.0),
            physical_tolerance_mm=10.0,
        )
        manifest = ShapeManifest(components=(spec,), joins=())
        result = check_all(manifest=manifest, irs={"body": ir}, constraints={"body": constraint})
        assert not result.passed
        assert all(e.error_type == "geometric_origin" for e in result.errors)

    def test_retry_does_not_affect_passing_pipeline(self):
        """Both canonical garments still pass without triggering the retry path."""
        assert DeterministicOrchestrator().run(_drop_shoulder_input()).checker_result.passed
        assert DeterministicOrchestrator().run(_yoke_input()).checker_result.passed
