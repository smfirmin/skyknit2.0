"""
Tests for skyknit/parser/parser.py.

Unit tests (CI-safe, no LLM calls) cover all assembly helpers with manually
constructed ParsedPattern fixtures.  Integration tests (3) require ANTHROPIC_API_KEY
and are skipped in CI.

Test gauges and stitch counts are self-consistent but deliberately simple —
they do not reproduce exact pipeline-generated values.
"""

from __future__ import annotations

import os

import pytest

from skyknit.checker.checker import check_all
from skyknit.parser.parser import (
    ParsedComponent,
    ParsedJoin,
    ParsedOperation,
    ParsedPattern,
    ParserInput,
    ParserOutput,
    PatternParser,
    _assemble,
    _assemble_component_ir,
    _assemble_constraints,
    _assemble_join,
    _back_calculate_dimensions,
    _build_parsed_pattern,
    _infer_edges,
    _infer_shape_type,
)
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.ir import OpType
from skyknit.schemas.manifest import Handedness, ShapeType
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.topology.types import EdgeType, JoinType
from skyknit.utilities.conversion import row_count_to_physical, stitch_count_to_physical
from skyknit.utilities.types import Gauge

# ── Shared test fixtures ───────────────────────────────────────────────────────

_GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
_MOTIF = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
_YARN = YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0)
_PRECISION = PrecisionPreference.MEDIUM

_PARSER_INPUT = ParserInput(
    pattern_text="",  # unused by unit tests; LLM integration tests override this
    gauge=_GAUGE,
    stitch_motif=_MOTIF,
    yarn_spec=_YARN,
    precision=_PRECISION,
)


def _make_drop_shoulder_parsed() -> ParsedPattern:
    """Drop-shoulder pullover: body + left/right sleeves with PICKUP joins."""
    body = ParsedComponent(
        name="body",
        handedness="NONE",
        starting_stitch_count=80,
        ending_stitch_count=0,
        operations=(
            ParsedOperation(
                "CAST_ON", stitch_count_after=80, row_count=None, parameters={"count": 80}
            ),
            ParsedOperation("WORK_EVEN", stitch_count_after=80, row_count=100, parameters={}),
            ParsedOperation(
                "BIND_OFF", stitch_count_after=0, row_count=None, parameters={"count": 80}
            ),
        ),
    )
    left_sleeve = ParsedComponent(
        name="left_sleeve",
        handedness="LEFT",
        starting_stitch_count=40,
        ending_stitch_count=0,
        operations=(
            ParsedOperation(
                "PICKUP_STITCHES", stitch_count_after=40, row_count=None, parameters={"count": 40}
            ),
            ParsedOperation("DECREASE_SECTION", stitch_count_after=20, row_count=80, parameters={}),
            ParsedOperation(
                "BIND_OFF", stitch_count_after=0, row_count=None, parameters={"count": 20}
            ),
        ),
    )
    right_sleeve = ParsedComponent(
        name="right_sleeve",
        handedness="RIGHT",
        starting_stitch_count=40,
        ending_stitch_count=0,
        operations=(
            ParsedOperation(
                "PICKUP_STITCHES", stitch_count_after=40, row_count=None, parameters={"count": 40}
            ),
            ParsedOperation("DECREASE_SECTION", stitch_count_after=20, row_count=80, parameters={}),
            ParsedOperation(
                "BIND_OFF", stitch_count_after=0, row_count=None, parameters={"count": 20}
            ),
        ),
    )
    joins = (
        ParsedJoin("j_left_armhole", "PICKUP", "body.left_armhole", "left_sleeve.top", {}),
        ParsedJoin("j_right_armhole", "PICKUP", "body.right_armhole", "right_sleeve.top", {}),
    )
    return ParsedPattern(
        components=(body, left_sleeve, right_sleeve),
        joins=joins,
        gauge=(20.0, 28.0),
        garment_type_hint="top-down-drop-shoulder-pullover",
    )


def _make_yoke_parsed() -> ParsedPattern:
    """Yoke pullover: yoke + body (CONTINUATION) + standalone sleeves."""
    yoke = ParsedComponent(
        name="yoke",
        handedness="NONE",
        starting_stitch_count=40,
        ending_stitch_count=80,
        operations=(
            ParsedOperation(
                "CAST_ON", stitch_count_after=40, row_count=None, parameters={"count": 40}
            ),
            ParsedOperation("INCREASE_SECTION", stitch_count_after=80, row_count=30, parameters={}),
        ),
    )
    body = ParsedComponent(
        name="body",
        handedness="NONE",
        starting_stitch_count=80,
        ending_stitch_count=0,
        operations=(
            ParsedOperation("WORK_EVEN", stitch_count_after=80, row_count=100, parameters={}),
            ParsedOperation(
                "BIND_OFF", stitch_count_after=0, row_count=None, parameters={"count": 80}
            ),
        ),
    )
    left_sleeve = ParsedComponent(
        name="left_sleeve",
        handedness="LEFT",
        starting_stitch_count=40,
        ending_stitch_count=0,
        operations=(
            ParsedOperation(
                "CAST_ON", stitch_count_after=40, row_count=None, parameters={"count": 40}
            ),
            ParsedOperation("DECREASE_SECTION", stitch_count_after=20, row_count=80, parameters={}),
            ParsedOperation(
                "BIND_OFF", stitch_count_after=0, row_count=None, parameters={"count": 20}
            ),
        ),
    )
    right_sleeve = ParsedComponent(
        name="right_sleeve",
        handedness="RIGHT",
        starting_stitch_count=40,
        ending_stitch_count=0,
        operations=(
            ParsedOperation(
                "CAST_ON", stitch_count_after=40, row_count=None, parameters={"count": 40}
            ),
            ParsedOperation("DECREASE_SECTION", stitch_count_after=20, row_count=80, parameters={}),
            ParsedOperation(
                "BIND_OFF", stitch_count_after=0, row_count=None, parameters={"count": 20}
            ),
        ),
    )
    joins = (ParsedJoin("j_yoke_body", "CONTINUATION", "yoke.body_join", "body.top", {}),)
    return ParsedPattern(
        components=(yoke, body, left_sleeve, right_sleeve),
        joins=joins,
        gauge=(20.0, 28.0),
        garment_type_hint="top-down-yoke-pullover",
    )


# ── TestBuildParsedPattern ─────────────────────────────────────────────────────


class TestBuildParsedPattern:
    def test_round_trips_component_name(self):
        raw = {
            "components": [
                {
                    "name": "body",
                    "handedness": "NONE",
                    "starting_stitch_count": 80,
                    "ending_stitch_count": 0,
                    "operations": [
                        {
                            "op_type": "CAST_ON",
                            "stitch_count_after": 80,
                            "row_count": None,
                            "parameters": {"count": 80},
                        },
                    ],
                }
            ],
            "joins": [],
        }
        pp = _build_parsed_pattern(raw)
        assert pp.components[0].name == "body"
        assert pp.components[0].starting_stitch_count == 80
        assert pp.components[0].operations[0].op_type == "CAST_ON"

    def test_null_gauge_becomes_none(self):
        raw = {"components": [], "joins": [], "gauge": None}
        pp = _build_parsed_pattern(raw)
        assert pp.gauge is None

    def test_gauge_parsed_to_tuple(self):
        raw = {
            "components": [],
            "joins": [],
            "gauge": {"stitches_per_inch": 20.0, "rows_per_inch": 28.0},
        }
        pp = _build_parsed_pattern(raw)
        assert pp.gauge == (20.0, 28.0)

    def test_missing_gauge_key_becomes_none(self):
        raw = {"components": [], "joins": []}
        pp = _build_parsed_pattern(raw)
        assert pp.gauge is None

    def test_garment_type_hint_passed_through(self):
        raw = {"components": [], "joins": [], "garment_type_hint": "drop-shoulder"}
        pp = _build_parsed_pattern(raw)
        assert pp.garment_type_hint == "drop-shoulder"

    def test_join_fields_parsed(self):
        raw = {
            "components": [],
            "joins": [
                {
                    "id": "j_left_armhole",
                    "join_type": "PICKUP",
                    "edge_a_ref": "body.left_armhole",
                    "edge_b_ref": "left_sleeve.top",
                    "parameters": {},
                }
            ],
        }
        pp = _build_parsed_pattern(raw)
        j = pp.joins[0]
        assert j.id == "j_left_armhole"
        assert j.join_type == "PICKUP"
        assert j.edge_a_ref == "body.left_armhole"


# ── TestShapeTypeInference ─────────────────────────────────────────────────────


class TestShapeTypeInference:
    def _comp(self, ops: list[tuple[str, int | None]]) -> ParsedComponent:
        """Build a minimal ParsedComponent with given (op_type, stitch_count_after) pairs."""
        return ParsedComponent(
            name="x",
            handedness="NONE",
            starting_stitch_count=ops[0][1] or 0,
            ending_stitch_count=ops[-1][1] or 0,
            operations=tuple(ParsedOperation(op, sts, None, {}) for op, sts in ops),
        )

    def test_uniform_stitch_count_is_cylinder(self):
        comp = self._comp([("CAST_ON", 80), ("WORK_EVEN", 80), ("BIND_OFF", 0)])
        assert _infer_shape_type(comp) == ShapeType.CYLINDER

    def test_varying_stitch_count_is_trapezoid(self):
        comp = self._comp([("CAST_ON", 80), ("DECREASE_SECTION", 40), ("BIND_OFF", 0)])
        assert _infer_shape_type(comp) == ShapeType.TRAPEZOID

    def test_empty_operations_is_cylinder(self):
        comp = ParsedComponent("x", "NONE", 0, 0, ())
        assert _infer_shape_type(comp) == ShapeType.CYLINDER

    def test_single_nonzero_count_is_cylinder(self):
        comp = self._comp([("CAST_ON", 80), ("BIND_OFF", 0)])
        assert _infer_shape_type(comp) == ShapeType.CYLINDER

    def test_increasing_then_uniform_is_trapezoid(self):
        # yoke-style: CAST_ON 40 then INCREASE_SECTION 80
        comp = self._comp([("CAST_ON", 40), ("INCREASE_SECTION", 80)])
        assert _infer_shape_type(comp) == ShapeType.TRAPEZOID


# ── TestEdgeTypeInference ──────────────────────────────────────────────────────


class TestEdgeTypeInference:
    def _sleeve_joins(self) -> tuple[ParsedJoin, ...]:
        return (
            ParsedJoin("j_left_armhole", "PICKUP", "body.left_armhole", "left_sleeve.top", {}),
            ParsedJoin("j_right_armhole", "PICKUP", "body.right_armhole", "right_sleeve.top", {}),
        )

    def test_cast_on_first_op_gives_cast_on_edge(self):
        comp = ParsedComponent(
            "body",
            "NONE",
            80,
            0,
            (
                ParsedOperation("CAST_ON", 80, None, {"count": 80}),
                ParsedOperation("WORK_EVEN", 80, 100, {}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 80}),
            ),
        )
        edges = _infer_edges(comp, ())
        assert edges[0].edge_type == EdgeType.CAST_ON
        assert edges[0].name == "neck"

    def test_bind_off_last_op_gives_bound_off_edge(self):
        comp = ParsedComponent(
            "body",
            "NONE",
            80,
            0,
            (
                ParsedOperation("CAST_ON", 80, None, {"count": 80}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 80}),
            ),
        )
        edges = _infer_edges(comp, ())
        bound_off = [e for e in edges if e.edge_type == EdgeType.BOUND_OFF]
        assert len(bound_off) == 1
        assert bound_off[0].name == "hem"

    def test_left_handedness_gives_cuff_name(self):
        comp = ParsedComponent(
            "left_sleeve",
            "LEFT",
            40,
            0,
            (
                ParsedOperation("PICKUP_STITCHES", 40, None, {"count": 40}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 40}),
            ),
        )
        edges = _infer_edges(comp, self._sleeve_joins())
        bound_off = [e for e in edges if e.edge_type == EdgeType.BOUND_OFF]
        assert bound_off[0].name == "cuff"

    def test_right_handedness_gives_cuff_name(self):
        comp = ParsedComponent(
            "right_sleeve",
            "RIGHT",
            40,
            0,
            (
                ParsedOperation("PICKUP_STITCHES", 40, None, {"count": 40}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 40}),
            ),
        )
        edges = _infer_edges(comp, self._sleeve_joins())
        bound_off = [e for e in edges if e.edge_type == EdgeType.BOUND_OFF]
        assert bound_off[0].name == "cuff"

    def test_pickup_downstream_gives_live_stitch_first_edge(self):
        comp = ParsedComponent(
            "left_sleeve",
            "LEFT",
            40,
            0,
            (
                ParsedOperation("PICKUP_STITCHES", 40, None, {"count": 40}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 40}),
            ),
        )
        edges = _infer_edges(comp, self._sleeve_joins())
        live = [e for e in edges if e.edge_type == EdgeType.LIVE_STITCH]
        assert any(e.name == "top" and e.join_ref == "j_left_armhole" for e in live)

    def test_selvedge_edges_from_pickup_source_joins(self):
        comp = ParsedComponent(
            "body",
            "NONE",
            80,
            0,
            (
                ParsedOperation("CAST_ON", 80, None, {"count": 80}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 80}),
            ),
        )
        edges = _infer_edges(comp, self._sleeve_joins())
        selvedge = [e for e in edges if e.edge_type == EdgeType.SELVEDGE]
        names = {e.name for e in selvedge}
        assert "left_armhole" in names
        assert "right_armhole" in names

    def test_continuation_upstream_gives_live_stitch_last_edge(self):
        # Yoke is edge_a of a CONTINUATION join → last edge is LIVE_STITCH
        comp = ParsedComponent(
            "yoke",
            "NONE",
            40,
            80,
            (
                ParsedOperation("CAST_ON", 40, None, {"count": 40}),
                ParsedOperation("INCREASE_SECTION", 80, 30, {}),
            ),
        )
        joins = (ParsedJoin("j_yoke_body", "CONTINUATION", "yoke.body_join", "body.top", {}),)
        edges = _infer_edges(comp, joins)
        live_last = [
            e for e in edges if e.edge_type == EdgeType.LIVE_STITCH and e.name == "body_join"
        ]
        assert len(live_last) == 1
        assert live_last[0].join_ref == "j_yoke_body"


# ── TestDimensionBackCalculation ───────────────────────────────────────────────


class TestDimensionBackCalculation:
    def _body_comp(self) -> ParsedComponent:
        return ParsedComponent(
            "body",
            "NONE",
            80,
            0,
            (
                ParsedOperation("CAST_ON", 80, None, {}),
                ParsedOperation("WORK_EVEN", 80, 100, {}),
                ParsedOperation("BIND_OFF", 0, None, {}),
            ),
        )

    def _sleeve_comp(self) -> ParsedComponent:
        return ParsedComponent(
            "left_sleeve",
            "LEFT",
            40,
            0,
            (
                ParsedOperation("PICKUP_STITCHES", 40, None, {"count": 40}),
                ParsedOperation("DECREASE_SECTION", 20, 80, {}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 20}),
            ),
        )

    def test_cylinder_has_circumference_mm(self):
        dims = _back_calculate_dimensions(self._body_comp(), ShapeType.CYLINDER, _GAUGE)
        assert "circumference_mm" in dims
        assert "depth_mm" in dims
        expected = stitch_count_to_physical(80, _GAUGE)
        assert abs(dims["circumference_mm"] - expected) < 0.01

    def test_trapezoid_has_top_and_bottom_circumference(self):
        dims = _back_calculate_dimensions(self._sleeve_comp(), ShapeType.TRAPEZOID, _GAUGE)
        assert "top_circumference_mm" in dims
        assert "bottom_circumference_mm" in dims
        assert "depth_mm" in dims

    def test_trapezoid_bottom_uses_last_nonzero_count(self):
        # sleeve ends in BIND_OFF (sts=0), but bottom should come from DECREASE_SECTION (sts=20)
        dims = _back_calculate_dimensions(self._sleeve_comp(), ShapeType.TRAPEZOID, _GAUGE)
        expected = stitch_count_to_physical(20, _GAUGE)
        assert abs(dims["bottom_circumference_mm"] - expected) < 0.01

    def test_depth_mm_from_row_counts(self):
        dims = _back_calculate_dimensions(self._body_comp(), ShapeType.CYLINDER, _GAUGE)
        expected = row_count_to_physical(100, _GAUGE)
        assert abs(dims["depth_mm"] - expected) < 0.01


# ── TestComponentIRAssembly ────────────────────────────────────────────────────


class TestComponentIRAssembly:
    def test_body_ir_fields(self):
        comp = ParsedComponent(
            "body",
            "NONE",
            80,
            0,
            (
                ParsedOperation("CAST_ON", 80, None, {"count": 80}),
                ParsedOperation("WORK_EVEN", 80, 100, {}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 80}),
            ),
        )
        ir = _assemble_component_ir(comp)
        assert ir.component_name == "body"
        assert ir.handedness == Handedness.NONE
        assert ir.starting_stitch_count == 80
        assert ir.ending_stitch_count == 0
        assert ir.operations[0].op_type == OpType.CAST_ON

    def test_sleeve_ir_left_handedness(self):
        comp = ParsedComponent(
            "left_sleeve",
            "LEFT",
            40,
            0,
            (
                ParsedOperation("PICKUP_STITCHES", 40, None, {"count": 40}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 40}),
            ),
        )
        ir = _assemble_component_ir(comp)
        assert ir.handedness == Handedness.LEFT
        assert ir.operations[0].op_type == OpType.PICKUP_STITCHES

    def test_pickup_stitches_first_op_forces_starting_count_zero(self):
        # PICKUP_STITCHES starts with 0 live stitches; the op adds them.
        # The assembler must override whatever starting_stitch_count the LLM reported.
        comp = ParsedComponent(
            "left_sleeve",
            "LEFT",
            starting_stitch_count=40,  # LLM may report the pickup count here
            ending_stitch_count=0,
            operations=(
                ParsedOperation("PICKUP_STITCHES", 40, None, {"count": 40}),
                ParsedOperation("DECREASE_SECTION", 20, 80, {}),
                ParsedOperation("BIND_OFF", 0, None, {"count": 20}),
            ),
        )
        ir = _assemble_component_ir(comp)
        assert ir.starting_stitch_count == 0

    def test_bad_op_type_raises_value_error(self):
        comp = ParsedComponent(
            "x",
            "NONE",
            0,
            0,
            (ParsedOperation("INVALID_OP", None, None, {}),),
        )
        with pytest.raises(ValueError):
            _assemble_component_ir(comp)

    def test_parameters_promoted_to_mapping_proxy(self):
        comp = ParsedComponent(
            "body",
            "NONE",
            80,
            0,
            (ParsedOperation("CAST_ON", 80, None, {"count": 80}),),
        )
        ir = _assemble_component_ir(comp)
        from types import MappingProxyType

        assert isinstance(ir.operations[0].parameters, MappingProxyType)


# ── TestJoinAssembly ───────────────────────────────────────────────────────────


class TestJoinAssembly:
    def test_valid_pickup_join(self):
        pj = ParsedJoin("j_left_armhole", "PICKUP", "body.left_armhole", "left_sleeve.top", {})
        j = _assemble_join(pj)
        assert j.id == "j_left_armhole"
        assert j.join_type == JoinType.PICKUP
        assert j.edge_a_ref == "body.left_armhole"

    def test_valid_continuation_join(self):
        pj = ParsedJoin("j_yoke_body", "CONTINUATION", "yoke.body_join", "body.top", {})
        j = _assemble_join(pj)
        assert j.join_type == JoinType.CONTINUATION

    def test_bad_join_type_raises_value_error(self):
        pj = ParsedJoin("j_bad", "INVALID_JOIN", "a.x", "b.y", {})
        with pytest.raises(ValueError):
            _assemble_join(pj)


# ── TestHandedness ─────────────────────────────────────────────────────────────


class TestHandedness:
    def test_left_handedness(self):
        comp = ParsedComponent("left_sleeve", "LEFT", 40, 0, ())
        ir = _assemble_component_ir(comp)
        assert ir.handedness == Handedness.LEFT

    def test_right_handedness(self):
        comp = ParsedComponent("right_sleeve", "RIGHT", 40, 0, ())
        ir = _assemble_component_ir(comp)
        assert ir.handedness == Handedness.RIGHT

    def test_none_handedness(self):
        comp = ParsedComponent("body", "NONE", 80, 0, ())
        ir = _assemble_component_ir(comp)
        assert ir.handedness == Handedness.NONE

    def test_bad_handedness_raises_value_error(self):
        comp = ParsedComponent("x", "INVALID", 0, 0, ())
        with pytest.raises(ValueError):
            _assemble_component_ir(comp)


# ── TestConstraintAssembly ─────────────────────────────────────────────────────


class TestConstraintAssembly:
    def test_keyed_by_component_name(self):
        names = ("body", "left_sleeve", "right_sleeve")
        constraints = _assemble_constraints(names, _GAUGE, _MOTIF, _YARN, _PRECISION)
        assert set(constraints.keys()) == set(names)

    def test_tolerance_derived_from_gauge(self):
        names = ("body",)
        constraints = _assemble_constraints(names, _GAUGE, _MOTIF, _YARN, _PRECISION)
        # Physical tolerance must be positive
        assert constraints["body"].physical_tolerance_mm > 0

    def test_gauge_preserved(self):
        names = ("body",)
        constraints = _assemble_constraints(names, _GAUGE, _MOTIF, _YARN, _PRECISION)
        assert constraints["body"].gauge == _GAUGE


# ── TestAssembly ───────────────────────────────────────────────────────────────


class TestAssembly:
    def test_drop_shoulder_assembly_check_all_passes(self):
        parsed = _make_drop_shoulder_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        result = check_all(out.manifest, out.irs, out.constraints)
        assert result.passed, f"check_all errors: {result.errors}"

    def test_yoke_assembly_check_all_passes(self):
        parsed = _make_yoke_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        result = check_all(out.manifest, out.irs, out.constraints)
        assert result.passed, f"check_all errors: {result.errors}"

    def test_output_has_correct_component_count(self):
        parsed = _make_drop_shoulder_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        assert len(out.manifest.components) == 3
        assert len(out.irs) == 3
        assert len(out.constraints) == 3

    def test_output_has_correct_join_count(self):
        parsed = _make_drop_shoulder_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        assert len(out.manifest.joins) == 2

    def test_parsed_pattern_preserved_in_output(self):
        parsed = _make_drop_shoulder_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        assert out.parsed_pattern is parsed

    def test_parser_output_satisfies_protocol(self):
        parsed = _make_drop_shoulder_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        assert isinstance(out, ParserOutput)

    def test_yoke_irs_contain_all_components(self):
        parsed = _make_yoke_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        assert "yoke" in out.irs
        assert "body" in out.irs
        assert "left_sleeve" in out.irs
        assert "right_sleeve" in out.irs

    def test_body_inferred_as_cylinder(self):
        parsed = _make_drop_shoulder_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        body_spec = next(s for s in out.manifest.components if s.name == "body")
        assert body_spec.shape_type == ShapeType.CYLINDER

    def test_sleeve_inferred_as_trapezoid(self):
        parsed = _make_drop_shoulder_parsed()
        out = _assemble(parsed, _PARSER_INPUT)
        sleeve_spec = next(s for s in out.manifest.components if s.name == "left_sleeve")
        assert sleeve_spec.shape_type == ShapeType.TRAPEZOID

    def test_bad_op_type_raises_parse_error_on_assembly(self):
        bad_comp = ParsedComponent(
            "body",
            "NONE",
            80,
            0,
            (ParsedOperation("NOT_AN_OP", 80, None, {}),),
        )
        bad_parsed = ParsedPattern(
            components=(bad_comp,),
            joins=(),
            gauge=None,
            garment_type_hint=None,
        )
        with pytest.raises((ValueError, KeyError)):
            _assemble(bad_parsed, _PARSER_INPUT)


# ── Integration tests (skipped in CI without ANTHROPIC_API_KEY) ───────────────

_SKIP_LLM = pytest.mark.skipif(
    os.environ.get("ANTHROPIC_API_KEY") is None,
    reason="ANTHROPIC_API_KEY not set — LLM integration tests skipped",
)


@_SKIP_LLM
def test_llm_parser_satisfies_protocol():
    from skyknit.parser.parser import LLMPatternParser

    parser = LLMPatternParser()
    assert isinstance(parser, PatternParser)


@_SKIP_LLM
def test_llm_round_trip_drop_shoulder():
    """generate_pattern() → LLMPatternParser → check_all() must pass."""
    from skyknit.api.generate import generate_pattern
    from skyknit.api.validate import validate_pattern

    pattern = generate_pattern(
        "top-down-drop-shoulder-pullover",
        {
            "chest_circumference_mm": 914.4,
            "body_length_mm": 457.2,
            "sleeve_length_mm": 495.3,
            "upper_arm_circumference_mm": 381.0,
            "wrist_circumference_mm": 152.4,
        },
        _GAUGE,
        _MOTIF,
        _YARN,
    )
    report = validate_pattern(pattern, _GAUGE, _MOTIF, _YARN)
    assert report.passed, f"Round-trip failed:\n{report.parse_error}\n{report.checker_result}"


@_SKIP_LLM
def test_llm_round_trip_yoke():
    """generate_pattern() → LLMPatternParser → check_all() must pass for yoke pullover."""
    from skyknit.api.generate import generate_pattern
    from skyknit.api.validate import validate_pattern

    pattern = generate_pattern(
        "top-down-yoke-pullover",
        {
            "chest_circumference_mm": 914.4,
            "body_length_mm": 457.2,
            "yoke_depth_mm": 228.6,
            "sleeve_length_mm": 495.3,
            "upper_arm_circumference_mm": 381.0,
            "wrist_circumference_mm": 152.4,
        },
        _GAUGE,
        _MOTIF,
        _YARN,
    )
    report = validate_pattern(pattern, _GAUGE, _MOTIF, _YARN)
    assert report.passed, f"Round-trip failed:\n{report.parse_error}\n{report.checker_result}"
