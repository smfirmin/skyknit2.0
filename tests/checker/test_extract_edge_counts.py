"""Tests for checker.simulate.extract_edge_counts."""

from __future__ import annotations

from skyknit.checker.simulate import extract_edge_counts
from skyknit.schemas.ir import (
    ComponentIR,
    Operation,
    OpType,
    make_bind_off,
    make_cast_on,
    make_work_even,
)
from skyknit.schemas.manifest import ComponentSpec, Handedness, ShapeType
from skyknit.topology.types import Edge, EdgeType, Join, JoinType


def _make_ir(operations: tuple, starting: int, ending: int, name: str = "body") -> ComponentIR:
    return ComponentIR(
        component_name=name,
        handedness=Handedness.NONE,
        operations=operations,
        starting_stitch_count=starting,
        ending_stitch_count=ending,
    )


def _make_spec(
    name: str, edges: tuple, shape_type: ShapeType = ShapeType.CYLINDER
) -> ComponentSpec:
    return ComponentSpec(
        name=name,
        shape_type=shape_type,
        dimensions={"circumference_mm": 914.4, "depth_mm": 457.2},
        edges=edges,
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


class TestSimpleTopBottom:
    def test_receiving_component_live_stitch_top(self):
        """Body receives live stitches (no CAST_ON op) — top LIVE_STITCH → starting count."""
        ir = _make_ir(
            (make_work_even(row_count=20, stitch_count=80), make_bind_off(80)),
            starting=80,
            ending=0,
        )
        spec = _make_spec(
            "body",
            (
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_body_join"),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["top"] == 80
        assert counts["bottom"] == 0

    def test_casting_on_component_live_stitch_bottom(self):
        """Yoke casts on and passes live stitches downstream — bottom LIVE_STITCH → ending count."""
        ir = _make_ir(
            (make_cast_on(80), make_work_even(row_count=10, stitch_count=80)),
            starting=80,
            ending=80,
            name="yoke",
        )
        spec = _make_spec(
            "yoke",
            (
                Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref=None),
                Edge(name="bottom", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_body_join"),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["top"] == 80  # CAST_ON edge → starting_stitch_count
        assert counts["bottom"] == 80  # LIVE_STITCH (output) → ending_stitch_count

    def test_bound_off_bottom(self):
        """BOUND_OFF edge always maps to ending_stitch_count."""
        ir = _make_ir(
            (make_cast_on(60), make_bind_off(60)),
            starting=60,
            ending=0,
        )
        spec = _make_spec(
            "sleeve",
            (
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_sleeve_join"),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["bottom"] == 0

    def test_open_edge_maps_to_ending(self):
        """OPEN edge (e.g. cuff left on needle) maps to ending_stitch_count."""
        ir = _make_ir(
            (make_work_even(row_count=30, stitch_count=48),),
            starting=48,
            ending=48,
        )
        spec = _make_spec(
            "sleeve",
            (
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="yoke_sleeve_join"),
                Edge(name="cuff", edge_type=EdgeType.OPEN, join_ref=None),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["cuff"] == 48


class TestIntermediateEdges:
    def test_held_stitch_underarm(self):
        """HOLD operation label matches edge name → held stitch count."""
        hold_op = Operation(
            op_type=OpType.HOLD,
            parameters={"count": 12, "label": "underarm"},
            row_count=None,
            stitch_count_after=None,
        )
        ir = _make_ir(
            (
                make_cast_on(80),
                make_work_even(row_count=10, stitch_count=80),
                hold_op,
                make_bind_off(68),
            ),
            starting=80,
            ending=0,
        )
        spec = _make_spec(
            "body",
            (
                Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref=None),
                Edge(name="underarm", edge_type=EdgeType.LIVE_STITCH, join_ref="underarm_join"),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["underarm"] == 12

    def test_separate_labels_captured(self):
        """SEPARATE labels for two underarm edges are both captured."""
        sep_left = Operation(
            op_type=OpType.SEPARATE,
            parameters={"count": 12, "label": "left_underarm"},
            row_count=None,
            stitch_count_after=None,
        )
        sep_right = Operation(
            op_type=OpType.SEPARATE,
            parameters={"count": 12, "label": "right_underarm"},
            row_count=None,
            stitch_count_after=None,
        )
        ir = _make_ir(
            (
                make_cast_on(100),
                make_work_even(row_count=10, stitch_count=100),
                sep_left,
                sep_right,
                make_bind_off(76),
            ),
            starting=100,
            ending=0,
        )
        spec = _make_spec(
            "yoke",
            (
                Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref=None),
                Edge(name="left_underarm", edge_type=EdgeType.LIVE_STITCH, join_ref="left_join"),
                Edge(name="right_underarm", edge_type=EdgeType.LIVE_STITCH, join_ref="right_join"),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["left_underarm"] == 12
        assert counts["right_underarm"] == 12

    def test_held_edge_takes_priority_over_live_stitch_heuristic(self):
        """An edge whose name is in held_stitches always uses the held count,
        regardless of its EdgeType."""
        hold_op = Operation(
            op_type=OpType.HOLD,
            parameters={"count": 20, "label": "shoulder"},
            row_count=None,
            stitch_count_after=None,
        )
        ir = _make_ir(
            (make_cast_on(80), hold_op, make_bind_off(60)),
            starting=80,
            ending=0,
        )
        spec = _make_spec(
            "body",
            (
                Edge(name="top", edge_type=EdgeType.CAST_ON, join_ref=None),
                Edge(name="shoulder", edge_type=EdgeType.LIVE_STITCH, join_ref="shoulder_join"),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["shoulder"] == 20


class TestSelvedgeEdge:
    """SELVEDGE edges should return the total row count, not the stitch count."""

    def _body_ir_with_rows(self) -> ComponentIR:
        """Body IR with 3 row-producing operations (total 50 rows)."""
        return _make_ir(
            (
                make_cast_on(80),
                make_work_even(row_count=30, stitch_count=80),
                make_work_even(row_count=20, stitch_count=80),
                make_bind_off(80),
            ),
            starting=80,
            ending=0,
        )

    def test_selvedge_returns_row_count(self):
        """SELVEDGE edge → total row count from the IR, not the stitch count."""
        ir = self._body_ir_with_rows()
        spec = _make_spec(
            "body",
            (
                Edge(name="neck", edge_type=EdgeType.CAST_ON, join_ref=None),
                Edge(name="hem", edge_type=EdgeType.BOUND_OFF, join_ref=None),
                Edge(name="armhole", edge_type=EdgeType.SELVEDGE, join_ref="j_armhole"),
            ),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["armhole"] == 50  # 30 + 20 rows

    def test_selvedge_not_starting_stitch_count(self):
        """SELVEDGE edge value must differ from starting_stitch_count (80)."""
        ir = self._body_ir_with_rows()
        spec = _make_spec(
            "body",
            (Edge(name="armhole", edge_type=EdgeType.SELVEDGE, join_ref="j_armhole"),),
        )
        counts = extract_edge_counts(ir, spec)
        assert counts["armhole"] != 80  # starting_stitch_count is 80; row count is 50


class TestPickupDownstreamLiveStitch:
    """LIVE_STITCH edge_b of a PICKUP join → starting_stitch_count, not ending."""

    def _sleeve_ir(self) -> ComponentIR:
        """Sleeve IR: starts with CAST_ON (representing pickup), ends with BIND_OFF."""
        return ComponentIR(
            component_name="left_sleeve",
            handedness=Handedness.NONE,
            operations=(
                make_cast_on(60),
                make_work_even(row_count=40, stitch_count=60),
                make_bind_off(60),
            ),
            starting_stitch_count=60,
            ending_stitch_count=0,
        )

    def _pickup_join(self) -> Join:
        return Join(
            id="j_armhole",
            join_type=JoinType.PICKUP,
            edge_a_ref="body.armhole",
            edge_b_ref="left_sleeve.top",
        )

    def test_pickup_downstream_returns_starting_count(self):
        """LIVE_STITCH top edge (edge_b of PICKUP) → starting_stitch_count (60)."""
        ir = self._sleeve_ir()
        spec = _make_spec(
            "left_sleeve",
            (
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j_armhole"),
                Edge(name="cuff", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        counts = extract_edge_counts(ir, spec, joins=(self._pickup_join(),))
        assert counts["top"] == 60  # starting_stitch_count, not ending (0)

    def test_no_joins_falls_back_to_heuristic(self):
        """When joins=None, the old heuristic applies: first_op_is_cast_on → ending_stitch_count."""
        ir = self._sleeve_ir()
        spec = _make_spec(
            "left_sleeve",
            (
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref="j_armhole"),
                Edge(name="cuff", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        # Without join context, first_op_is_cast_on=True → ending_stitch_count=0
        counts = extract_edge_counts(ir, spec, joins=None)
        assert counts["top"] == 0  # old heuristic: ending_stitch_count


class TestReturnType:
    def test_returns_dict(self):
        ir = _make_ir(
            (make_work_even(row_count=10, stitch_count=80), make_bind_off(80)),
            starting=80,
            ending=0,
        )
        spec = _make_spec(
            "body",
            (
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
        )
        result = extract_edge_counts(ir, spec)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"top", "bottom"}
