"""Tests for checker.checker — check_all and CheckerResult."""

from __future__ import annotations

import pytest

from checker.checker import CheckerResult, check_all
from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from schemas.ir import ComponentIR, Operation, OpType, make_bind_off, make_cast_on, make_work_even
from schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from topology.types import Edge, EdgeType, Join, JoinType
from utilities.types import Gauge

# ── Shared fixtures ────────────────────────────────────────────────────────────

GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
MOTIF = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
YARN = YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0)
CONSTRAINT = ConstraintObject(
    gauge=GAUGE,
    stitch_motif=MOTIF,
    hard_constraints=(),
    yarn_spec=YARN,
    physical_tolerance_mm=10.0,
)


def _body_ir(stitch_count: int = 80) -> ComponentIR:
    return ComponentIR(
        component_name="body",
        handedness=Handedness.NONE,
        operations=(
            make_work_even(row_count=20, stitch_count=stitch_count),
            make_bind_off(stitch_count),
        ),
        starting_stitch_count=stitch_count,
        ending_stitch_count=0,
    )


def _yoke_ir(stitch_count: int = 80) -> ComponentIR:
    return ComponentIR(
        component_name="yoke",
        handedness=Handedness.NONE,
        operations=(
            make_cast_on(stitch_count),
            make_work_even(row_count=10, stitch_count=stitch_count),
        ),
        starting_stitch_count=stitch_count,
        ending_stitch_count=stitch_count,
    )


def _body_spec(stitch_count: int = 80) -> ComponentSpec:
    return ComponentSpec(
        name="body",
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": float(stitch_count * 5), "depth_mm": 457.2},
        edges=(
            Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_body_join"),
            Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
        ),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


def _yoke_spec(stitch_count: int = 80) -> ComponentSpec:
    return ComponentSpec(
        name="yoke",
        shape_type=ShapeType.CYLINDER,
        dimensions={"circumference_mm": float(stitch_count * 5), "depth_mm": 200.0},
        edges=(
            Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref=None),
            Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_body_join"),
        ),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


def _continuation_join(count: int = 80) -> Join:
    return Join(
        id="yoke_body_join",
        join_type=JoinType.CONTINUATION,
        edge_a_ref="yoke.bottom",
        edge_b_ref="body.top",
    )


class TestCheckerResult:
    def test_is_frozen(self):
        result = CheckerResult(passed=True, errors=())
        with pytest.raises(Exception):
            result.passed = False  # type: ignore[misc]

    def test_passed_true_when_no_errors(self):
        result = CheckerResult(passed=True, errors=())
        assert result.passed is True
        assert result.errors == ()


class TestCheckAllValid:
    def test_simple_valid_manifest_passes(self):
        manifest = ShapeManifest(
            components=(_yoke_spec(80), _body_spec(80)),
            joins=(_continuation_join(80),),
        )
        irs = {"yoke": _yoke_ir(80), "body": _body_ir(80)}
        constraints = {"yoke": CONSTRAINT, "body": CONSTRAINT}

        result = check_all(manifest, irs, constraints)
        assert result.passed is True
        assert result.errors == ()

    def test_returns_checker_result_type(self):
        manifest = ShapeManifest(
            components=(_body_spec(),),
            joins=(),
        )
        irs = {"body": _body_ir()}
        result = check_all(manifest, irs, {})
        assert isinstance(result, CheckerResult)

    def test_no_joins_no_join_errors(self):
        manifest = ShapeManifest(
            components=(_body_spec(),),
            joins=(),
        )
        result = check_all(manifest, {"body": _body_ir()}, {"body": CONSTRAINT})
        assert result.passed is True


class TestCheckAllComponentErrors:
    def test_missing_ir_produces_error(self):
        manifest = ShapeManifest(
            components=(_body_spec(),),
            joins=(),
        )
        result = check_all(manifest, {}, {})  # no IR provided
        assert result.passed is False
        assert any("no ComponentIR" in e.message for e in result.errors)

    def test_bad_stitch_count_produces_filler_error(self):
        """A BIND_OFF with wrong count → filler_origin error."""
        bad_ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(
                make_work_even(row_count=10, stitch_count=80),
                Operation(
                    op_type=OpType.BIND_OFF,
                    parameters={"count": 60},  # wrong — live count is 80
                    row_count=None,
                    stitch_count_after=0,
                ),
            ),
            starting_stitch_count=80,
            ending_stitch_count=0,
        )
        manifest = ShapeManifest(components=(_body_spec(),), joins=())
        result = check_all(manifest, {"body": bad_ir}, {"body": CONSTRAINT})
        assert result.passed is False
        assert any(e.error_type == "filler_origin" for e in result.errors)

    def test_errors_collected_from_all_components(self):
        """Errors from multiple components are all reported."""
        bad_ir_body = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(make_work_even(row_count=10, stitch_count=80),),
            starting_stitch_count=80,
            ending_stitch_count=99,  # wrong ending count
        )
        bad_ir_yoke = ComponentIR(
            component_name="yoke",
            handedness=Handedness.NONE,
            operations=(make_cast_on(80), make_work_even(row_count=5, stitch_count=80)),
            starting_stitch_count=80,
            ending_stitch_count=99,  # wrong ending count
        )
        manifest = ShapeManifest(
            components=(_yoke_spec(), _body_spec()),
            joins=(),
        )
        result = check_all(manifest, {"yoke": bad_ir_yoke, "body": bad_ir_body}, {})
        assert result.passed is False
        component_names = {e.component_name for e in result.errors}
        assert "body" in component_names
        assert "yoke" in component_names


class TestCheckAllJoinErrors:
    def test_join_mismatch_produces_geometric_error(self):
        """Yoke outputs 80 sts but body expects 60 → join error."""
        manifest = ShapeManifest(
            components=(_yoke_spec(80), _body_spec(60)),
            joins=(_continuation_join(),),
        )
        irs = {"yoke": _yoke_ir(80), "body": _body_ir(60)}
        constraints = {"yoke": CONSTRAINT, "body": CONSTRAINT}

        result = check_all(manifest, irs, constraints)
        assert result.passed is False
        join_errors = [e for e in result.errors if e.component_name == "yoke_body_join"]
        assert len(join_errors) >= 1
        assert join_errors[0].error_type == "geometric_origin"

    def test_tighter_tolerance_applied(self):
        """When components have different tolerances, the tighter one governs."""
        strict_constraint = ConstraintObject(
            gauge=GAUGE,
            stitch_motif=MOTIF,
            hard_constraints=(),
            yarn_spec=YARN,
            physical_tolerance_mm=1.0,  # very tight
        )
        # 2-stitch diff at 20 sts/inch ≈ 2.54mm > 1.0mm → should fail
        manifest = ShapeManifest(
            components=(_yoke_spec(80), _body_spec(80)),
            joins=(Join(
                id="yoke_body_join",
                join_type=JoinType.CONTINUATION,
                edge_a_ref="yoke.bottom",
                edge_b_ref="body.top",
            ),),
        )
        yoke_ir = ComponentIR(
            component_name="yoke",
            handedness=Handedness.NONE,
            operations=(make_cast_on(80), make_work_even(row_count=10, stitch_count=80)),
            starting_stitch_count=80,
            ending_stitch_count=80,
        )
        body_ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(make_work_even(row_count=20, stitch_count=78), make_bind_off(78)),
            starting_stitch_count=78,
            ending_stitch_count=0,
        )
        constraints = {"yoke": CONSTRAINT, "body": strict_constraint}
        result = check_all(manifest, {"yoke": yoke_ir, "body": body_ir}, constraints)
        assert result.passed is False
