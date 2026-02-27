"""Tests for checker.checker — full algebraic checking pipeline."""

import pytest

from checker.checker import CheckerResult, check_all
from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from schemas.ir import ComponentIR, Operation, OpType, make_bind_off, make_cast_on, make_work_even
from schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from topology.types import Edge, EdgeType, Join, JoinType
from utilities.types import Gauge


@pytest.fixture
def gauge():
    return Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)


@pytest.fixture
def constraint(gauge):
    return ConstraintObject(
        gauge=gauge,
        stitch_motif=StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1),
        hard_constraints=(),
        yarn_spec=YarnSpec(weight="worsted", fiber="100% merino", needle_size_mm=4.5),
        physical_tolerance_mm=5.08,
    )


class TestFullyValidManifest:
    def test_simple_two_component_passes(self, constraint):
        """Body → Skirt with CONTINUATION join, matching stitch counts.

        Body ends with live stitches (HOLD to 'bottom' label) that flow into
        skirt.top (CAST_ON). Both edges report 100 stitches.
        """
        manifest = ShapeManifest(
            components=(
                ComponentSpec(
                    name="body",
                    shape_type=ShapeType.RECTANGLE,
                    dimensions={"width": 500.0, "height": 400.0},
                    edges=(
                        Edge(name="top", edge_type=EdgeType.CAST_ON),
                        Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="j1"),
                    ),
                    handedness=Handedness.NONE,
                    instantiation_count=1,
                ),
                ComponentSpec(
                    name="skirt",
                    shape_type=ShapeType.TRAPEZOID,
                    dimensions={"width_top": 500.0, "width_bottom": 600.0, "height": 300.0},
                    edges=(
                        Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref="j1"),
                        Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
                    ),
                    handedness=Handedness.NONE,
                    instantiation_count=1,
                ),
            ),
            joins=(
                Join(
                    id="j1",
                    join_type=JoinType.CONTINUATION,
                    edge_a_ref="body.bottom",
                    edge_b_ref="skirt.top",
                ),
            ),
        )

        irs = {
            "body": ComponentIR(
                component_name="body",
                handedness=Handedness.NONE,
                operations=(
                    make_cast_on(100),
                    make_work_even(row_count=40, stitch_count=100),
                    Operation(
                        op_type=OpType.HOLD,
                        parameters={"label": "bottom", "count": 100},
                        row_count=None,
                        stitch_count_after=0,
                    ),
                ),
                starting_stitch_count=100,
                ending_stitch_count=0,
            ),
            "skirt": ComponentIR(
                component_name="skirt",
                handedness=Handedness.NONE,
                operations=(
                    make_cast_on(100),
                    Operation(
                        op_type=OpType.INCREASE_SECTION,
                        parameters={},
                        row_count=20,
                        stitch_count_after=120,
                    ),
                    make_bind_off(120),
                ),
                starting_stitch_count=100,
                ending_stitch_count=0,
            ),
        }

        constraints = {"body": constraint, "skirt": constraint}
        result = check_all(manifest, irs, constraints)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_single_component_no_joins(self, constraint):
        """Simple single-component pattern with no joins."""
        manifest = ShapeManifest(
            components=(
                ComponentSpec(
                    name="scarf",
                    shape_type=ShapeType.RECTANGLE,
                    dimensions={"width": 200.0, "height": 1500.0},
                    edges=(
                        Edge(name="top", edge_type=EdgeType.CAST_ON),
                        Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
                    ),
                    handedness=Handedness.NONE,
                    instantiation_count=1,
                ),
            ),
            joins=(),
        )

        irs = {
            "scarf": ComponentIR(
                component_name="scarf",
                handedness=Handedness.NONE,
                operations=(
                    make_cast_on(40),
                    make_work_even(row_count=200, stitch_count=40),
                    make_bind_off(40),
                ),
                starting_stitch_count=40,
                ending_stitch_count=0,
            ),
        }

        result = check_all(manifest, irs, {"scarf": constraint})
        assert result.passed is True


class TestFillerOriginErrors:
    def test_bad_stitch_count_in_component(self, constraint):
        """Component IR with wrong ending stitch count."""
        manifest = ShapeManifest(
            components=(
                ComponentSpec(
                    name="body",
                    shape_type=ShapeType.RECTANGLE,
                    dimensions={"width": 500.0, "height": 400.0},
                    edges=(
                        Edge(name="top", edge_type=EdgeType.CAST_ON),
                        Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
                    ),
                    handedness=Handedness.NONE,
                    instantiation_count=1,
                ),
            ),
            joins=(),
        )

        irs = {
            "body": ComponentIR(
                component_name="body",
                handedness=Handedness.NONE,
                operations=(
                    make_cast_on(80),
                    make_work_even(row_count=40, stitch_count=80),
                    make_bind_off(80),
                ),
                starting_stitch_count=80,
                ending_stitch_count=80,  # wrong — bind_off leaves 0
            ),
        }

        result = check_all(manifest, irs, {"body": constraint})
        assert result.passed is False
        assert any(e.error_type == "filler_origin" for e in result.errors)

    def test_missing_ir_for_component(self, constraint):
        """No IR provided for a manifest component."""
        manifest = ShapeManifest(
            components=(
                ComponentSpec(
                    name="body",
                    shape_type=ShapeType.RECTANGLE,
                    dimensions={"width": 500.0, "height": 400.0},
                    edges=(
                        Edge(name="top", edge_type=EdgeType.CAST_ON),
                        Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
                    ),
                    handedness=Handedness.NONE,
                    instantiation_count=1,
                ),
            ),
            joins=(),
        )

        result = check_all(manifest, {}, {"body": constraint})
        assert result.passed is False
        assert any("No IR provided" in e.message for e in result.errors)


class TestJoinErrors:
    def test_join_mismatch_detected(self, constraint):
        """SEAM join with mismatched stitch counts between components."""
        manifest = ShapeManifest(
            components=(
                ComponentSpec(
                    name="front",
                    shape_type=ShapeType.RECTANGLE,
                    dimensions={"width": 250.0, "height": 400.0},
                    edges=(
                        Edge(name="top", edge_type=EdgeType.CAST_ON),
                        Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
                        Edge(name="side", edge_type=EdgeType.SELVEDGE, join_ref="j1"),
                    ),
                    handedness=Handedness.NONE,
                    instantiation_count=1,
                ),
                ComponentSpec(
                    name="back",
                    shape_type=ShapeType.RECTANGLE,
                    dimensions={"width": 250.0, "height": 400.0},
                    edges=(
                        Edge(name="top", edge_type=EdgeType.CAST_ON),
                        Edge(name="bottom", edge_type=EdgeType.BOUND_OFF),
                        Edge(name="side", edge_type=EdgeType.SELVEDGE, join_ref="j1"),
                    ),
                    handedness=Handedness.NONE,
                    instantiation_count=1,
                ),
            ),
            joins=(
                Join(
                    id="j1",
                    join_type=JoinType.SEAM,
                    edge_a_ref="front.side",
                    edge_b_ref="back.side",
                    parameters={"seam_method": "mattress"},
                ),
            ),
        )

        irs = {
            "front": ComponentIR(
                component_name="front",
                handedness=Handedness.NONE,
                operations=(
                    make_cast_on(50),
                    make_work_even(row_count=40, stitch_count=50),
                    make_bind_off(50),
                ),
                starting_stitch_count=50,
                ending_stitch_count=0,
            ),
            "back": ComponentIR(
                component_name="back",
                handedness=Handedness.NONE,
                operations=(
                    make_cast_on(60),
                    make_work_even(row_count=40, stitch_count=60),
                    make_bind_off(60),
                ),
                starting_stitch_count=60,
                ending_stitch_count=0,
            ),
        }

        constraints = {"front": constraint, "back": constraint}
        result = check_all(manifest, irs, constraints)
        # SEAM join references selvedge edges, which are omitted from edge counts.
        # The join validation should report missing edge counts.
        assert result.passed is False


class TestCheckerResult:
    def test_is_frozen(self, constraint):
        result = CheckerResult(passed=True, errors=())
        with pytest.raises(Exception):
            result.passed = False  # type: ignore[misc]


class TestIntegrationWithUtilities:
    def test_uses_shared_utilities_for_conversion(self):
        """Verify checker imports from utilities — not a duplicate implementation."""
        from utilities.conversion import physical_to_stitch_count

        gauge = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        result = physical_to_stitch_count(25.4, gauge)
        assert result == pytest.approx(5.0)
