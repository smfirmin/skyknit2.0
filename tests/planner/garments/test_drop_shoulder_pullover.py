"""Tests for planner.garments.drop_shoulder_pullover — make_drop_shoulder_pullover."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from skyknit.fillers.filler import DeterministicFiller, FillerInput
from skyknit.planner.garments.drop_shoulder_pullover import make_drop_shoulder_pullover
from skyknit.planner.manifest_builder import build_shape_manifest
from skyknit.schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from skyknit.schemas.garment import GarmentSpec
from skyknit.schemas.manifest import Handedness, ShapeType
from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec
from skyknit.topology.types import EdgeType, JoinType
from skyknit.utilities.types import Gauge
from skyknit.validator.phase1 import validate_phase1

PROPORTION_SPEC = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
    precision=PrecisionPreference.MEDIUM,
)

MEASUREMENTS = {
    "chest_circumference_mm": 914.4,
    "body_length_mm": 457.2,
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


class TestMakeDropShoulderPullover:
    def test_returns_garment_spec(self):
        spec = make_drop_shoulder_pullover()
        assert isinstance(spec, GarmentSpec)

    def test_garment_type_label(self):
        spec = make_drop_shoulder_pullover()
        assert spec.garment_type == "top-down-drop-shoulder-pullover"

    def test_component_names_and_order(self):
        spec = make_drop_shoulder_pullover()
        names = [c.name for c in spec.components]
        assert names == ["body", "left_sleeve", "right_sleeve"]

    def test_exactly_two_joins(self):
        spec = make_drop_shoulder_pullover()
        assert len(spec.joins) == 2

    def test_join_ids_and_types(self):
        spec = make_drop_shoulder_pullover()
        join_map = {j.id: j for j in spec.joins}
        assert "j_left_armhole" in join_map
        assert "j_right_armhole" in join_map
        assert join_map["j_left_armhole"].join_type == JoinType.PICKUP
        assert join_map["j_right_armhole"].join_type == JoinType.PICKUP

    def test_join_edge_refs(self):
        spec = make_drop_shoulder_pullover()
        join_map = {j.id: j for j in spec.joins}
        assert join_map["j_left_armhole"].edge_a_ref == "body.left_armhole"
        assert join_map["j_left_armhole"].edge_b_ref == "left_sleeve.top"
        assert join_map["j_right_armhole"].edge_a_ref == "body.right_armhole"
        assert join_map["j_right_armhole"].edge_b_ref == "right_sleeve.top"

    def test_body_is_cylinder(self):
        spec = make_drop_shoulder_pullover()
        body = next(c for c in spec.components if c.name == "body")
        assert body.shape_type == ShapeType.CYLINDER
        assert body.handedness == Handedness.NONE

    def test_body_has_four_edges(self):
        spec = make_drop_shoulder_pullover()
        body = next(c for c in spec.components if c.name == "body")
        assert len(body.edges) == 4

    def test_body_edge_types(self):
        spec = make_drop_shoulder_pullover()
        body = next(c for c in spec.components if c.name == "body")
        edge_map = {e.name: e for e in body.edges}
        assert edge_map["neck"].edge_type == EdgeType.CAST_ON
        assert edge_map["hem"].edge_type == EdgeType.BOUND_OFF
        assert edge_map["left_armhole"].edge_type == EdgeType.SELVEDGE
        assert edge_map["right_armhole"].edge_type == EdgeType.SELVEDGE

    def test_body_armhole_join_refs(self):
        spec = make_drop_shoulder_pullover()
        body = next(c for c in spec.components if c.name == "body")
        edge_map = {e.name: e for e in body.edges}
        assert edge_map["left_armhole"].join_id == "j_left_armhole"
        assert edge_map["right_armhole"].join_id == "j_right_armhole"
        assert edge_map["neck"].join_id is None
        assert edge_map["hem"].join_id is None

    def test_body_dimension_rules(self):
        spec = make_drop_shoulder_pullover()
        body = next(c for c in spec.components if c.name == "body")
        rule_keys = {r.dimension_key for r in body.dimension_rules}
        assert "circumference_mm" in rule_keys
        assert "depth_mm" in rule_keys

    def test_left_sleeve_handedness(self):
        spec = make_drop_shoulder_pullover()
        left = next(c for c in spec.components if c.name == "left_sleeve")
        assert left.handedness == Handedness.LEFT
        assert left.shape_type == ShapeType.TRAPEZOID

    def test_right_sleeve_handedness(self):
        spec = make_drop_shoulder_pullover()
        right = next(c for c in spec.components if c.name == "right_sleeve")
        assert right.handedness == Handedness.RIGHT
        assert right.shape_type == ShapeType.TRAPEZOID

    def test_sleeve_top_edges_reference_joins(self):
        spec = make_drop_shoulder_pullover()
        left = next(c for c in spec.components if c.name == "left_sleeve")
        right = next(c for c in spec.components if c.name == "right_sleeve")
        left_top = next(e for e in left.edges if e.name == "top")
        right_top = next(e for e in right.edges if e.name == "top")
        assert left_top.join_id == "j_left_armhole"
        assert right_top.join_id == "j_right_armhole"

    def test_sleeve_cuffs_are_terminal(self):
        spec = make_drop_shoulder_pullover()
        for name in ("left_sleeve", "right_sleeve"):
            bp = next(c for c in spec.components if c.name == name)
            cuff = next(e for e in bp.edges if e.name == "cuff")
            assert cuff.edge_type == EdgeType.BOUND_OFF
            assert cuff.join_id is None

    def test_left_and_right_sleeve_dimension_rules_identical(self):
        spec = make_drop_shoulder_pullover()
        left = next(c for c in spec.components if c.name == "left_sleeve")
        right = next(c for c in spec.components if c.name == "right_sleeve")
        left_rules = {
            (r.dimension_key, r.measurement_key, r.ratio_key) for r in left.dimension_rules
        }
        right_rules = {
            (r.dimension_key, r.measurement_key, r.ratio_key) for r in right.dimension_rules
        }
        assert left_rules == right_rules

    def test_required_measurements_keys(self):
        spec = make_drop_shoulder_pullover()
        assert spec.required_measurements == frozenset(
            {
                "chest_circumference_mm",
                "body_length_mm",
                "sleeve_length_mm",
                "upper_arm_circumference_mm",
                "wrist_circumference_mm",
            }
        )

    def test_no_yoke_depth_required(self):
        """Drop shoulder has no yoke — yoke_depth_mm is not a required measurement."""
        spec = make_drop_shoulder_pullover()
        assert "yoke_depth_mm" not in spec.required_measurements


class TestDropShoulderIntegration:
    def test_manifest_passes_validate_phase1(self):
        """Produced manifest must pass Phase 1 geometric validation."""
        spec = make_drop_shoulder_pullover()
        manifest = build_shape_manifest(spec, PROPORTION_SPEC, MEASUREMENTS)
        result = validate_phase1(manifest)
        assert result.passed is True, f"validate_phase1 failed: {result.errors}"

    def test_deterministic_filler_succeeds_on_body(self):
        """Body with SELVEDGE armhole edges must fill without error."""
        spec = make_drop_shoulder_pullover()
        manifest = build_shape_manifest(spec, PROPORTION_SPEC, MEASUREMENTS)
        body = next(c for c in manifest.components if c.name == "body")
        joins = tuple(
            j for j in manifest.joins if "body." in j.edge_a_ref or "body." in j.edge_b_ref
        )
        fi = FillerInput(
            component_spec=body, constraint=CONSTRAINT, joins=joins, handedness=body.handedness
        )
        output = DeterministicFiller().fill(fi)
        assert output.ir is not None

    def test_deterministic_filler_succeeds_on_sleeves(self):
        """Both sleeves (TRAPEZOID) must fill without error."""
        spec = make_drop_shoulder_pullover()
        manifest = build_shape_manifest(spec, PROPORTION_SPEC, MEASUREMENTS)
        filler = DeterministicFiller()
        for name in ("left_sleeve", "right_sleeve"):
            comp = next(c for c in manifest.components if c.name == name)
            fi = FillerInput(
                component_spec=comp, constraint=CONSTRAINT, joins=(), handedness=comp.handedness
            )
            output = filler.fill(fi)
            assert output.ir is not None

    def test_sleeve_dimensions_computed(self):
        spec = make_drop_shoulder_pullover()
        manifest = build_shape_manifest(spec, PROPORTION_SPEC, MEASUREMENTS)
        left = next(c for c in manifest.components if c.name == "left_sleeve")
        assert left.dimensions["top_circumference_mm"] == pytest.approx(381.0 * 1.1)
        assert left.dimensions["bottom_circumference_mm"] == pytest.approx(152.4 * 1.05)
        assert left.dimensions["depth_mm"] == pytest.approx(495.3)

    def test_missing_measurement_raises_value_error(self):
        spec = make_drop_shoulder_pullover()
        bad_measurements = {k: v for k, v in MEASUREMENTS.items() if k != "sleeve_length_mm"}
        with pytest.raises(ValueError, match="sleeve_length_mm"):
            build_shape_manifest(spec, PROPORTION_SPEC, bad_measurements)
