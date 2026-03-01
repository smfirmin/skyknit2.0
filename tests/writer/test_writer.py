"""Tests for writer.writer — WriterInput, WriterOutput, TemplateWriter, PatternWriter."""

from __future__ import annotations

from types import MappingProxyType

import pytest

import skyknit.planner.garments  # noqa: F401 — triggers registration
from skyknit.fabric.module import FabricInput
from skyknit.orchestrator.pipeline import DeterministicOrchestrator, OrchestratorInput
from skyknit.planner.garments.registry import get
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.ir import ComponentIR, make_bind_off, make_cast_on, make_work_even
from skyknit.schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec
from skyknit.topology.types import Edge, EdgeType, Join, JoinType
from skyknit.utilities.types import Gauge
from skyknit.writer.writer import PatternWriter, TemplateWriter, WriterInput, WriterOutput

# ── Shared pipeline helpers ────────────────────────────────────────────────────


_PROPORTION = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
    precision=PrecisionPreference.MEDIUM,
)

_FABRIC = FabricInput(
    component_names=(),
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


def _drop_shoulder_output():
    oi = OrchestratorInput(
        garment_spec=get("top-down-drop-shoulder-pullover"),
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_DROP,
        fabric_input=_FABRIC,
    )
    return DeterministicOrchestrator().run(oi)


def _yoke_output():
    oi = OrchestratorInput(
        garment_spec=get("top-down-yoke-pullover"),
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS_YOKE,
        fabric_input=_FABRIC,
    )
    return DeterministicOrchestrator().run(oi)


def _writer_input_from(output) -> WriterInput:
    return WriterInput(
        manifest=output.manifest,
        irs=output.irs,
        component_order=output.component_order,
    )


# ── Minimal fixture helpers ────────────────────────────────────────────────────


def _make_spec(name: str, edges: tuple, handedness: Handedness = Handedness.NONE) -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions=MappingProxyType({"circumference_mm": 100.0, "depth_mm": 50.0}),
        edges=edges,
        handedness=handedness,
        instantiation_count=1,
    )


def _make_simple_ir(name: str, count: int, handedness: Handedness = Handedness.NONE) -> ComponentIR:
    return ComponentIR(
        component_name=name,
        handedness=handedness,
        operations=(make_cast_on(count), make_work_even(20, count), make_bind_off(count)),
        starting_stitch_count=count,
        ending_stitch_count=0,
    )


# ── WriterInput ────────────────────────────────────────────────────────────────


class TestWriterInput:
    def test_is_frozen(self):
        output = _drop_shoulder_output()
        wi = _writer_input_from(output)
        with pytest.raises((AttributeError, TypeError)):
            wi.component_order = []  # type: ignore[misc]

    def test_template_writer_satisfies_protocol(self):
        assert isinstance(TemplateWriter(), PatternWriter)


# ── Drop shoulder writer ───────────────────────────────────────────────────────


class TestDropShoulderWriter:
    def setup_method(self):
        output = _drop_shoulder_output()
        wi = _writer_input_from(output)
        self.wo = TemplateWriter().write(wi)
        self.order = output.component_order

    def test_returns_writer_output(self):
        assert isinstance(self.wo, WriterOutput)

    def test_three_sections(self):
        assert len(self.wo.sections) == 3

    def test_section_keys_match_component_order(self):
        assert set(self.wo.sections.keys()) == set(self.order)

    def test_cast_on_in_body_section(self):
        assert "Cast on" in self.wo.sections["body"]

    def test_work_even_in_body_section(self):
        assert "Work even" in self.wo.sections["body"]

    def test_bind_off_in_body_section(self):
        assert "Bind off" in self.wo.sections["body"]

    def test_pickup_instruction_in_left_sleeve(self):
        assert "Pick up" in self.wo.sections["left_sleeve"]

    def test_pickup_instruction_in_right_sleeve(self):
        assert "Pick up" in self.wo.sections["right_sleeve"]

    def test_left_handedness_in_left_sleeve(self):
        assert "left" in self.wo.sections["left_sleeve"].lower()

    def test_right_handedness_in_right_sleeve(self):
        assert "right" in self.wo.sections["right_sleeve"].lower()

    def test_full_pattern_sections_in_order(self):
        # Each section header should appear in component_order sequence in full_pattern.
        positions = [
            self.wo.full_pattern.index(name.replace("_", " ").title()) for name in self.order
        ]
        assert positions == sorted(positions)

    def test_bind_off_in_each_section(self):
        for section_text in self.wo.sections.values():
            assert "Bind off" in section_text


# ── Yoke pullover writer ───────────────────────────────────────────────────────


class TestYokeWriter:
    def setup_method(self):
        output = _yoke_output()
        wi = _writer_input_from(output)
        self.wo = TemplateWriter().write(wi)
        self.order = output.component_order

    def test_four_sections(self):
        assert len(self.wo.sections) == 4

    def test_section_keys_match_component_order(self):
        assert set(self.wo.sections.keys()) == set(self.order)

    def test_continuation_join_no_instruction_in_body(self):
        # CONTINUATION is INLINE — the body section should start directly
        # with operation prose (no separate join instruction line).
        body_text = self.wo.sections["body"]
        assert "Place next" not in body_text
        assert "Pick up" not in body_text

    def test_work_even_in_yoke_section(self):
        assert "Work even" in self.wo.sections["yoke"]

    def test_full_pattern_has_all_sections(self):
        for name in self.order:
            assert name.replace("_", " ").title() in self.wo.full_pattern


# ── Join-type-specific tests using minimal fixtures ───────────────────────────


class TestHeldStitchJoin:
    """HELD_STITCH join → 'holder' in downstream section."""

    def test_holder_in_downstream_section(self):
        # Upstream: body with LIVE_STITCH underarm edge
        # Downstream: sleeve with LIVE_STITCH top edge receiving held stitches
        body_spec = _make_spec(
            "body",
            (
                Edge(name="top", edge_type=EdgeType.CAST_ON),
                Edge(name="underarm", edge_type=EdgeType.LIVE_STITCH, join_ref="j_underarm"),
                Edge(name="hem", edge_type=EdgeType.BOUND_OFF),
            ),
        )
        sleeve_spec = _make_spec(
            "sleeve",
            (
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j_underarm"),
                Edge(name="cuff", edge_type=EdgeType.BOUND_OFF),
            ),
        )
        body_ir = ComponentIR(
            component_name="body",
            handedness=Handedness.NONE,
            operations=(make_cast_on(80), make_work_even(20, 80), make_bind_off(80)),
            starting_stitch_count=80,
            ending_stitch_count=0,
        )
        sleeve_ir = ComponentIR(
            component_name="sleeve",
            handedness=Handedness.NONE,
            operations=(make_work_even(40, 60), make_bind_off(60)),
            starting_stitch_count=60,
            ending_stitch_count=0,
        )
        join = Join(
            id="j_underarm",
            join_type=JoinType.HELD_STITCH,
            edge_a_ref="body.underarm",
            edge_b_ref="sleeve.top",
        )
        manifest = ShapeManifest(
            components=(body_spec, sleeve_spec),
            joins=(join,),
        )
        wi = WriterInput(
            manifest=manifest,
            irs={"body": body_ir, "sleeve": sleeve_ir},
            component_order=["body", "sleeve"],
        )
        wo = TemplateWriter().write(wi)
        assert "holder" in wo.sections["sleeve"].lower()


class TestPickupJoinNoRedundantCastOn:
    """PICKUP join: Writer should not emit a CAST_ON op after the pick-up instruction."""

    def setup_method(self):
        output = _drop_shoulder_output()
        wi = _writer_input_from(output)
        self.wo = TemplateWriter().write(wi)

    def test_no_redundant_cast_on_in_pickup_sleeve(self):
        # left_sleeve is joined via PICKUP — the join instruction already says
        # "Pick up and knit N sts".  The CAST_ON op should NOT also be rendered.
        assert "Cast on" not in self.wo.sections["left_sleeve"]
        assert "Cast on" not in self.wo.sections["right_sleeve"]

    def test_pickup_sleeve_still_has_shaping(self):
        # Suppressing CAST_ON must not eat any shaping operations.
        assert "Decrease to" in self.wo.sections["left_sleeve"]
        assert "Decrease to" in self.wo.sections["right_sleeve"]


class TestSeamJoin:
    """SEAM join → seam note in header of both sections."""

    def test_seam_note_in_section_headers(self):
        left_spec = _make_spec("left_front", (Edge(name="side", edge_type=EdgeType.BOUND_OFF),))
        right_spec = _make_spec("right_front", (Edge(name="side", edge_type=EdgeType.BOUND_OFF),))
        left_ir = _make_simple_ir("left_front", 60)
        right_ir = _make_simple_ir("right_front", 60)
        seam_join = Join(
            id="j_side_seam",
            join_type=JoinType.SEAM,
            edge_a_ref="left_front.side",
            edge_b_ref="right_front.side",
            parameters={"seam_method": "mattress_stitch"},
        )
        manifest = ShapeManifest(
            components=(left_spec, right_spec),
            joins=(seam_join,),
        )
        wi = WriterInput(
            manifest=manifest,
            irs={"left_front": left_ir, "right_front": right_ir},
            component_order=["left_front", "right_front"],
        )
        wo = TemplateWriter().write(wi)
        # Both sections should have a seam note in their header line.
        left_header = wo.sections["left_front"].splitlines()[0]
        right_header = wo.sections["right_front"].splitlines()[0]
        assert "seam" in left_header.lower() or "Seam" in left_header
        assert "seam" in right_header.lower() or "Seam" in right_header
