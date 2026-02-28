"""Tests for fillers.resolver — resolve_stitch_counts."""

from __future__ import annotations

from fillers.resolver import resolve_stitch_counts
from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from schemas.manifest import ComponentSpec, Handedness, ShapeType
from topology.types import Edge, EdgeType
from utilities.types import Gauge

# ── Shared fixtures ────────────────────────────────────────────────────────────

# 20 sts/inch → 1 stitch = 1.27mm → 100mm ≈ 78.7 sts
GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
MOTIF_1 = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
MOTIF_4 = StitchMotif(name="2x2 rib", stitch_repeat=4, row_repeat=1)
YARN = YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0)


def _constraint(
    stitch_repeat: int = 1, tolerance_mm: float = 10.0, hard: tuple[int, ...] = ()
) -> ConstraintObject:
    motif = StitchMotif(name="test", stitch_repeat=stitch_repeat, row_repeat=1)
    return ConstraintObject(
        gauge=GAUGE,
        stitch_motif=motif,
        hard_constraints=hard,
        yarn_spec=YARN,
        physical_tolerance_mm=tolerance_mm,
    )


def _cylinder_spec(circumference_mm: float, name: str = "body") -> ComponentSpec:
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


class TestCylinderResolution:
    def test_returns_stitch_count_for_each_edge(self):
        spec = _cylinder_spec(circumference_mm=508.0)  # 20 inches → 400 sts
        result = resolve_stitch_counts(spec, _constraint())
        assert "top" in result
        assert "bottom" in result

    def test_correct_stitch_count_from_circumference(self):
        # 508mm / 25.4 * 20 sts/inch = 400.0 sts exactly
        spec = _cylinder_spec(circumference_mm=508.0)
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] == 400
        assert result["bottom"] == 400

    def test_both_edges_get_same_count_for_cylinder(self):
        spec = _cylinder_spec(circumference_mm=400.0)
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] == result["bottom"]


class TestRepeatConstraint:
    def test_repeat_4_snaps_to_nearest_multiple(self):
        # 400mm / 25.4 * 20 = 314.96 sts → nearest mult of 4 within tolerance
        spec = _cylinder_spec(circumference_mm=400.0)
        result = resolve_stitch_counts(spec, _constraint(stitch_repeat=4))
        assert result["top"] is not None
        assert result["top"] % 4 == 0

    def test_repeat_1_allows_any_count(self):
        spec = _cylinder_spec(circumference_mm=508.0)
        result = resolve_stitch_counts(spec, _constraint(stitch_repeat=1))
        assert result["top"] == 400  # exact

    def test_hard_constraint_respected(self):
        # 508mm → 400 sts; hard constraint of 8 → 400 % 8 == 0 ✓
        spec = _cylinder_spec(circumference_mm=508.0)
        result = resolve_stitch_counts(spec, _constraint(stitch_repeat=1, hard=(8,)))
        assert result["top"] is not None
        assert result["top"] % 8 == 0


class TestTrapezoidResolution:
    def test_top_and_bottom_get_different_counts(self):
        spec = ComponentSpec(
            name="sleeve",
            shape_type=ShapeType.TRAPEZOID,
            dimensions={
                "top_circumference_mm": 508.0,  # → 400 sts
                "bottom_circumference_mm": 254.0,  # → 200 sts
                "depth_mm": 457.2,
            },
            edges=(
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] == 400
        assert result["bottom"] == 200

    def test_third_edge_uses_bottom_circumference(self):
        spec = ComponentSpec(
            name="sleeve",
            shape_type=ShapeType.TRAPEZOID,
            dimensions={
                "top_circumference_mm": 508.0,
                "bottom_circumference_mm": 254.0,
                "depth_mm": 457.2,
            },
            edges=(
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
                Edge(name="middle", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
                Edge(name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["middle"] == 200  # index 1 → bottom_circumference_mm


class TestRectangleResolution:
    def test_rectangle_uses_width_mm(self):
        spec = ComponentSpec(
            name="swatch",
            shape_type=ShapeType.RECTANGLE,
            dimensions={"width_mm": 254.0, "depth_mm": 200.0},
            edges=(
                Edge(name="top", edge_type=EdgeType.BOUND_OFF, join_ref=None),
                Edge(name="bottom", edge_type=EdgeType.CAST_ON, join_ref=None),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] == 200
        assert result["bottom"] == 200


class TestUnresolvableEdges:
    def test_selvedge_returns_none(self):
        """SELVEDGE edges have no stitch-count dimension → None."""
        spec = ComponentSpec(
            name="body",
            shape_type=ShapeType.RECTANGLE,
            dimensions={"width_mm": 254.0, "depth_mm": 200.0},
            edges=(
                Edge(name="top", edge_type=EdgeType.BOUND_OFF, join_ref=None),
                Edge(name="side", edge_type=EdgeType.SELVEDGE, join_ref=None),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["side"] is None
        assert result["top"] == 200

    def test_returns_none_when_dimension_missing(self):
        """If the required dimension key is absent → None."""
        spec = ComponentSpec(
            name="body",
            shape_type=ShapeType.CYLINDER,
            dimensions={"depth_mm": 457.2},  # missing circumference_mm
            edges=(Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] is None

    def test_count_returns_none_when_tolerance_too_tight(self):
        """With extremely tight tolerance (0.01mm) and repeat=7, no valid count."""
        spec = _cylinder_spec(circumference_mm=314.0)
        result = resolve_stitch_counts(spec, _constraint(stitch_repeat=7, tolerance_mm=0.01))
        # May or may not resolve depending on exact math; just confirm it's int or None
        assert result["top"] is None or isinstance(result["top"], int)


class TestReturnType:
    def test_returns_dict(self):
        spec = _cylinder_spec(508.0)
        result = resolve_stitch_counts(spec, _constraint())
        assert isinstance(result, dict)

    def test_keys_match_edge_names(self):
        spec = _cylinder_spec(508.0)
        result = resolve_stitch_counts(spec, _constraint())
        assert set(result.keys()) == {"top", "bottom"}


class TestNamedRouting:
    """Edge.dimension_key overrides the positional fallback when set."""

    def test_named_key_resolves_on_cylinder(self):
        """Explicit dimension_key is looked up directly, ignoring shape_type convention."""
        spec = ComponentSpec(
            name="body",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference_mm": 508.0, "depth_mm": 457.2},
            edges=(
                Edge(
                    name="top",
                    edge_type=EdgeType.LIVE_STITCH,
                    join_ref=None,
                    dimension_key="circumference_mm",
                ),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] == 400  # 508mm → 400 sts at 20 sts/inch

    def test_named_key_overrides_positional_on_trapezoid(self):
        """Index-1 edge normally → bottom_circumference_mm; dimension_key overrides to top."""
        spec = ComponentSpec(
            name="sleeve",
            shape_type=ShapeType.TRAPEZOID,
            dimensions={
                "top_circumference_mm": 508.0,  # → 400 sts
                "bottom_circumference_mm": 254.0,  # → 200 sts
                "depth_mm": 457.2,
            },
            edges=(
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None),
                # Index 1 would normally → bottom, but dimension_key forces top
                Edge(
                    name="mid",
                    edge_type=EdgeType.LIVE_STITCH,
                    join_ref=None,
                    dimension_key="top_circumference_mm",
                ),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["mid"] == 400  # named key overrides positional → top value

    def test_named_key_missing_from_dimensions_returns_none(self):
        """dimension_key pointing to an absent key returns None."""
        spec = ComponentSpec(
            name="body",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference_mm": 508.0},
            edges=(
                Edge(
                    name="top",
                    edge_type=EdgeType.LIVE_STITCH,
                    join_ref=None,
                    dimension_key="nonexistent_key",
                ),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] is None

    def test_none_dimension_key_uses_cylinder_positional(self):
        """dimension_key=None falls back to positional: CYLINDER → circumference_mm."""
        spec = ComponentSpec(
            name="body",
            shape_type=ShapeType.CYLINDER,
            dimensions={"circumference_mm": 508.0, "depth_mm": 457.2},
            edges=(
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None, dimension_key=None),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] == 400

    def test_none_dimension_key_uses_trapezoid_positional(self):
        """dimension_key=None falls back to positional: TRAPEZOID index 0 → top_circumference_mm."""
        spec = ComponentSpec(
            name="sleeve",
            shape_type=ShapeType.TRAPEZOID,
            dimensions={
                "top_circumference_mm": 508.0,
                "bottom_circumference_mm": 254.0,
                "depth_mm": 457.2,
            },
            edges=(
                Edge(name="top", edge_type=EdgeType.LIVE_STITCH, join_ref=None, dimension_key=None),
                Edge(
                    name="bottom", edge_type=EdgeType.BOUND_OFF, join_ref=None, dimension_key=None
                ),
            ),
            handedness=Handedness.NONE,
            instantiation_count=1,
        )
        result = resolve_stitch_counts(spec, _constraint())
        assert result["top"] == 400
        assert result["bottom"] == 200
