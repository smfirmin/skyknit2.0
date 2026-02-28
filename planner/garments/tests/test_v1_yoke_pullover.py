"""Tests for planner.garments.v1_yoke_pullover — make_v1_yoke_pullover."""

from __future__ import annotations

from planner.garments.v1_yoke_pullover import make_v1_yoke_pullover
from schemas.garment import GarmentSpec
from schemas.manifest import Handedness, ShapeType
from topology.types import EdgeType, JoinType


class TestMakeV1YokePullover:
    def test_returns_garment_spec(self):
        spec = make_v1_yoke_pullover()
        assert isinstance(spec, GarmentSpec)

    def test_garment_type_label(self):
        spec = make_v1_yoke_pullover()
        assert spec.garment_type == "top-down-yoke-pullover"

    def test_component_names_and_order(self):
        spec = make_v1_yoke_pullover()
        names = [c.name for c in spec.components]
        assert names == ["yoke", "body", "left_sleeve", "right_sleeve"]

    def test_exactly_one_join(self):
        spec = make_v1_yoke_pullover()
        assert len(spec.joins) == 1

    def test_join_id_and_type(self):
        spec = make_v1_yoke_pullover()
        join = spec.joins[0]
        assert join.id == "j_yoke_body"
        assert join.join_type == JoinType.CONTINUATION

    def test_join_edge_refs(self):
        spec = make_v1_yoke_pullover()
        join = spec.joins[0]
        assert join.edge_a_ref == "yoke.body_join"
        assert join.edge_b_ref == "body.top"

    def test_yoke_is_cylinder(self):
        spec = make_v1_yoke_pullover()
        yoke = next(c for c in spec.components if c.name == "yoke")
        assert yoke.shape_type == ShapeType.CYLINDER
        assert yoke.handedness == Handedness.NONE

    def test_yoke_edges(self):
        spec = make_v1_yoke_pullover()
        yoke = next(c for c in spec.components if c.name == "yoke")
        edge_map = {e.name: e for e in yoke.edges}
        assert edge_map["neck"].edge_type == EdgeType.CAST_ON
        assert edge_map["neck"].join_id is None
        assert edge_map["body_join"].edge_type == EdgeType.LIVE_STITCH
        assert edge_map["body_join"].join_id == "j_yoke_body"

    def test_body_top_references_same_join(self):
        spec = make_v1_yoke_pullover()
        body = next(c for c in spec.components if c.name == "body")
        top_edge = next(e for e in body.edges if e.name == "top")
        assert top_edge.join_id == "j_yoke_body"

    def test_body_hem_is_terminal(self):
        spec = make_v1_yoke_pullover()
        body = next(c for c in spec.components if c.name == "body")
        hem_edge = next(e for e in body.edges if e.name == "hem")
        assert hem_edge.edge_type == EdgeType.BOUND_OFF
        assert hem_edge.join_id is None

    def test_left_sleeve_handedness(self):
        spec = make_v1_yoke_pullover()
        left = next(c for c in spec.components if c.name == "left_sleeve")
        assert left.handedness == Handedness.LEFT
        assert left.shape_type == ShapeType.TRAPEZOID

    def test_right_sleeve_handedness(self):
        spec = make_v1_yoke_pullover()
        right = next(c for c in spec.components if c.name == "right_sleeve")
        assert right.handedness == Handedness.RIGHT
        assert right.shape_type == ShapeType.TRAPEZOID

    def test_sleeves_are_standalone(self):
        """V1 sleeve joins are out-of-scope; all sleeve edges have join_id=None."""
        spec = make_v1_yoke_pullover()
        for name in ("left_sleeve", "right_sleeve"):
            bp = next(c for c in spec.components if c.name == name)
            for edge in bp.edges:
                assert edge.join_id is None, f"{name}.{edge.name} should have no join"

    def test_required_measurements_keys(self):
        spec = make_v1_yoke_pullover()
        assert spec.required_measurements == frozenset(
            {
                "chest_circumference_mm",
                "body_length_mm",
                "yoke_depth_mm",
                "sleeve_length_mm",
                "upper_arm_circumference_mm",
                "wrist_circumference_mm",
            }
        )

    def test_yoke_dimension_rules_reference_body_ease(self):
        spec = make_v1_yoke_pullover()
        yoke = next(c for c in spec.components if c.name == "yoke")
        circ_rule = next(r for r in yoke.dimension_rules if r.dimension_key == "circumference_mm")
        assert circ_rule.ratio_key == "body_ease"
        assert circ_rule.measurement_key == "chest_circumference_mm"

    def test_yoke_and_body_share_circumference_formula(self):
        """Ensures yoke.circumference_mm == body.circumference_mm for same measurements."""
        spec = make_v1_yoke_pullover()
        yoke = next(c for c in spec.components if c.name == "yoke")
        body = next(c for c in spec.components if c.name == "body")
        yoke_rule = next(r for r in yoke.dimension_rules if r.dimension_key == "circumference_mm")
        body_rule = next(r for r in body.dimension_rules if r.dimension_key == "circumference_mm")
        assert yoke_rule.measurement_key == body_rule.measurement_key
        assert yoke_rule.ratio_key == body_rule.ratio_key
