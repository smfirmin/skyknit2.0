"""Tests for fillers.filler — FillerInput, FillerOutput, DeterministicFiller."""

from __future__ import annotations

import pytest

from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from schemas.ir import OpType
from schemas.manifest import ComponentSpec, Handedness, ShapeType
from topology.types import Edge, EdgeType
from utilities.types import Gauge
from checker import check_all, CheckerResult
from fillers.filler import DeterministicFiller, FillerInput, FillerOutput, StitchFiller

# ── Shared fixtures ────────────────────────────────────────────────────────────

GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
CONSTRAINT = ConstraintObject(
    gauge=GAUGE,
    stitch_motif=StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1),
    hard_constraints=(),
    yarn_spec=YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0),
    physical_tolerance_mm=10.0,
)


def _cylinder_spec(circumference_mm: float = 508.0, name: str = "body") -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": circumference_mm, "depth_mm": 457.2},
        edges=(
            Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
            Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
        ),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


def _trapezoid_spec(name: str = "sleeve") -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.TRAPEZOID,
        dimensions={
            "top_circumference_mm": 508.0,
            "bottom_circumference_mm": 254.0,
            "depth_mm": 457.2,
        },
        edges=(
            Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
            Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
        ),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


class TestFillerInput:
    def test_is_frozen(self):
        fi = FillerInput(
            component_spec=_cylinder_spec(),
            constraint=CONSTRAINT,
            joins=(),
            handedness=Handedness.NONE,
        )
        with pytest.raises(Exception):
            fi.handedness = Handedness.LEFT  # type: ignore[misc]


class TestFillerOutput:
    def test_is_frozen(self):
        filler = DeterministicFiller()
        fi = FillerInput(_cylinder_spec(), CONSTRAINT, (), Handedness.NONE)
        output = filler.fill(fi)
        with pytest.raises(Exception):
            output.ir = None  # type: ignore[assignment]


class TestDeterministicFillerValid:
    def test_produces_filler_output(self):
        filler = DeterministicFiller()
        fi = FillerInput(_cylinder_spec(), CONSTRAINT, (), Handedness.NONE)
        output = filler.fill(fi)
        assert isinstance(output, FillerOutput)

    def test_resolved_counts_are_populated(self):
        filler = DeterministicFiller()
        fi = FillerInput(_cylinder_spec(508.0), CONSTRAINT, (), Handedness.NONE)
        output = filler.fill(fi)
        assert output.resolved_counts["top"] == 400
        assert output.resolved_counts["bottom"] == 400

    def test_cylinder_ir_has_work_even(self):
        filler = DeterministicFiller()
        fi = FillerInput(_cylinder_spec(), CONSTRAINT, (), Handedness.NONE)
        output = filler.fill(fi)
        op_types = [op.op_type for op in output.ir.operations]
        assert OpType.CAST_ON in op_types
        assert OpType.WORK_EVEN in op_types
        assert OpType.BIND_OFF in op_types

    def test_tapered_ir_has_taper(self):
        filler = DeterministicFiller()
        fi = FillerInput(_trapezoid_spec(), CONSTRAINT, (), Handedness.NONE)
        output = filler.fill(fi)
        op_types = [op.op_type for op in output.ir.operations]
        assert OpType.TAPER in op_types

    def test_handedness_propagated(self):
        filler = DeterministicFiller()
        fi = FillerInput(_trapezoid_spec("left_sleeve"), CONSTRAINT, (), Handedness.LEFT)
        output = filler.fill(fi)
        assert output.ir.handedness == Handedness.LEFT


class TestCheckerIntegration:
    def test_deterministic_filler_ir_passes_checker(self):
        """IR produced by DeterministicFiller must pass the Algebraic Checker."""
        from schemas.manifest import ShapeManifest

        spec = _cylinder_spec()
        filler = DeterministicFiller()
        fi = FillerInput(spec, CONSTRAINT, (), Handedness.NONE)
        output = filler.fill(fi)

        manifest = ShapeManifest(components=(spec,), joins=())
        result = check_all(
            manifest=manifest,
            irs={"body": output.ir},
            constraints={"body": CONSTRAINT},
        )
        assert result.passed is True, f"Checker failed: {result.errors}"

    def test_tapered_ir_passes_checker(self):
        from schemas.manifest import ShapeManifest

        spec = _trapezoid_spec()
        filler = DeterministicFiller()
        fi = FillerInput(spec, CONSTRAINT, (), Handedness.NONE)
        output = filler.fill(fi)

        manifest = ShapeManifest(components=(spec,), joins=())
        result = check_all(
            manifest=manifest,
            irs={"sleeve": output.ir},
            constraints={"sleeve": CONSTRAINT},
        )
        assert result.passed is True, f"Checker failed: {result.errors}"


class TestSymmetricMirroring:
    def test_mirror_produces_opposite_handedness(self):
        from fillers.ir_builder import mirror_component_ir

        filler = DeterministicFiller()
        fi = FillerInput(_trapezoid_spec("left_sleeve"), CONSTRAINT, (), Handedness.LEFT)
        output = filler.fill(fi)

        mirrored = mirror_component_ir(output.ir)
        assert mirrored.handedness == Handedness.RIGHT

    def test_mirrored_pair_has_matching_stitch_counts(self):
        from fillers.ir_builder import mirror_component_ir

        filler = DeterministicFiller()
        fi = FillerInput(_trapezoid_spec("left_sleeve"), CONSTRAINT, (), Handedness.LEFT)
        output = filler.fill(fi)

        mirrored = mirror_component_ir(output.ir)
        assert mirrored.starting_stitch_count == output.ir.starting_stitch_count
        assert mirrored.ending_stitch_count == output.ir.ending_stitch_count


class TestProtocolConformance:
    def test_deterministic_filler_satisfies_protocol(self):
        assert isinstance(DeterministicFiller(), StitchFiller)
