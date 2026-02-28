"""Tests for planner.planner — PlannerInput, PlannerOutput, DeterministicPlanner."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from checker import check_all
from fillers.filler import DeterministicFiller, FillerInput
from planner.garments.v1_yoke_pullover import make_v1_yoke_pullover
from planner.planner import DeterministicPlanner, Planner, PlannerInput, PlannerOutput
from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from schemas.manifest import ShapeManifest
from schemas.proportion import PrecisionPreference, ProportionSpec
from utilities.types import Gauge

GARMENT_SPEC = make_v1_yoke_pullover()

PROPORTION_SPEC = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
    precision=PrecisionPreference.MEDIUM,
)

MEASUREMENTS = {
    "chest_circumference_mm": 914.4,
    "body_length_mm": 457.2,
    "yoke_depth_mm": 203.2,
    "sleeve_length_mm": 495.3,
    "upper_arm_circumference_mm": 381.0,
    "wrist_circumference_mm": 152.4,
}

GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
CONSTRAINT = ConstraintObject(
    gauge=GAUGE,
    stitch_motif=StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1),
    hard_constraints=(),
    yarn_spec=YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0),
    physical_tolerance_mm=10.0,
)


class TestPlannerInput:
    def test_is_frozen(self):
        pi = PlannerInput(
            garment_spec=GARMENT_SPEC,
            proportion_spec=PROPORTION_SPEC,
            measurements=MEASUREMENTS,
        )
        with pytest.raises(Exception):
            pi.measurements = {}  # type: ignore[misc]


class TestPlannerOutput:
    def test_is_frozen(self):
        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        with pytest.raises(Exception):
            output.manifest = None  # type: ignore[assignment]


class TestDeterministicPlanner:
    def test_returns_planner_output(self):
        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        assert isinstance(output, PlannerOutput)

    def test_component_list_matches_garment_spec_order(self):
        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        assert output.component_list == ["yoke", "body", "left_sleeve", "right_sleeve"]

    def test_manifest_is_shape_manifest(self):
        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        assert isinstance(output.manifest, ShapeManifest)

    def test_manifest_component_count(self):
        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        assert len(output.manifest.components) == 4

    def test_component_list_matches_manifest_components(self):
        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        manifest_names = [c.name for c in output.manifest.components]
        assert output.component_list == manifest_names


class TestProtocolConformance:
    def test_deterministic_planner_satisfies_protocol(self):
        assert isinstance(DeterministicPlanner(), Planner)


class TestPlannerIntegration:
    def test_manifest_passes_validate_phase1(self):
        """Manifest produced by DeterministicPlanner must pass Phase 1 validation."""
        from validator.phase1 import validate_phase1

        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        result = validate_phase1(output.manifest)
        assert result.passed is True, f"validate_phase1 failed: {result.errors}"

    def test_end_to_end_yoke_and_body_pass_checker(self):
        """Manifest → DeterministicFiller (yoke + body) → check_all passes."""
        planner = DeterministicPlanner()
        pi = PlannerInput(GARMENT_SPEC, PROPORTION_SPEC, MEASUREMENTS)
        output = planner.plan(pi)
        manifest = output.manifest

        filler = DeterministicFiller()
        irs = {}
        constraints = {}
        for comp in manifest.components:
            if comp.name not in ("yoke", "body"):
                continue
            joins = tuple(
                j
                for j in manifest.joins
                if comp.name in (j.edge_a_ref.split(".")[0], j.edge_b_ref.split(".")[0])
            )
            fi = FillerInput(
                component_spec=comp,
                constraint=CONSTRAINT,
                joins=joins,
                handedness=comp.handedness,
            )
            fill_out = filler.fill(fi)
            irs[comp.name] = fill_out.ir
            constraints[comp.name] = CONSTRAINT

        # Build a sub-manifest with only the filled components
        filled_components = tuple(c for c in manifest.components if c.name in irs)
        sub_manifest = ShapeManifest(components=filled_components, joins=manifest.joins)

        result = check_all(manifest=sub_manifest, irs=irs, constraints=constraints)
        assert result.passed is True, f"check_all failed: {result.errors}"
