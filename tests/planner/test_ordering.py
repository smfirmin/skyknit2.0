"""Tests for planner.ordering — derive_component_order."""

from __future__ import annotations

from types import MappingProxyType

import pytest

import skyknit.planner.garments  # noqa: F401 — triggers registration
from skyknit.planner.garments.registry import get
from skyknit.planner.manifest_builder import build_shape_manifest
from skyknit.planner.ordering import derive_component_order
from skyknit.schemas.manifest import ComponentSpec, Handedness, ShapeManifest, ShapeType
from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec
from skyknit.topology.types import Edge, EdgeType, Join, JoinType

# ── Shared fixtures ────────────────────────────────────────────────────────────

_PROPORTION = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
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


def _minimal_spec(name: str) -> ComponentSpec:
    """Create a minimal ComponentSpec for ordering tests — no real dimensions needed."""
    return ComponentSpec(
        name=name,
        shape_type=ShapeType.CYLINDER,
        dimensions=MappingProxyType({"circumference_mm": 500.0, "depth_mm": 400.0}),
        edges=(Edge(name="top", edge_type=EdgeType.CAST_ON),),
        handedness=Handedness.NONE,
        instantiation_count=1,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestDeriveComponentOrder:
    def test_drop_shoulder_body_before_sleeves(self):
        spec = get("top-down-drop-shoulder-pullover")
        manifest = build_shape_manifest(spec, _PROPORTION, _MEASUREMENTS_DROP)
        order = derive_component_order(manifest)
        body_idx = order.index("body")
        assert order.index("left_sleeve") > body_idx
        assert order.index("right_sleeve") > body_idx

    def test_yoke_before_body(self):
        spec = get("top-down-yoke-pullover")
        manifest = build_shape_manifest(spec, _PROPORTION, _MEASUREMENTS_YOKE)
        order = derive_component_order(manifest)
        assert order.index("yoke") < order.index("body")

    def test_all_components_present(self):
        spec = get("top-down-drop-shoulder-pullover")
        manifest = build_shape_manifest(spec, _PROPORTION, _MEASUREMENTS_DROP)
        order = derive_component_order(manifest)
        component_names = [c.name for c in manifest.components]
        assert sorted(order) == sorted(component_names)

    def test_no_joins_preserves_tuple_order(self):
        """When no joins exist, tuple order is the tiebreaker."""
        a = _minimal_spec("alpha")
        b = _minimal_spec("beta")
        c = _minimal_spec("gamma")
        manifest = ShapeManifest(components=(a, b, c), joins=())
        assert derive_component_order(manifest) == ["alpha", "beta", "gamma"]

    def test_seam_join_does_not_constrain_order(self):
        """SEAM is symmetric — neither component is forced to come before the other."""
        a = _minimal_spec("piece_a")
        b = _minimal_spec("piece_b")
        seam = Join(
            id="j_seam",
            join_type=JoinType.SEAM,
            edge_a_ref="piece_a.top",
            edge_b_ref="piece_b.top",
        )
        # (a, b) order
        manifest_ab = ShapeManifest(components=(a, b), joins=(seam,))
        assert derive_component_order(manifest_ab) == ["piece_a", "piece_b"]
        # (b, a) order — SEAM should not force a before b
        manifest_ba = ShapeManifest(components=(b, a), joins=(seam,))
        assert derive_component_order(manifest_ba) == ["piece_b", "piece_a"]

    def test_tuple_order_preserved_within_tier(self):
        """Components in the same tier (no cross-dependency) keep original tuple order."""
        a = _minimal_spec("first")
        b = _minimal_spec("second")
        c = _minimal_spec("third")
        # No joins → all in tier 0 → original order
        manifest = ShapeManifest(components=(a, b, c), joins=())
        assert derive_component_order(manifest) == ["first", "second", "third"]

    def test_cycle_raises_value_error(self):
        """A→B and B→A creates a cycle and should raise ValueError."""
        a = _minimal_spec("comp_a")
        b = _minimal_spec("comp_b")
        join_ab = Join(
            id="j_ab",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="comp_a.top",
            edge_b_ref="comp_b.top",
        )
        join_ba = Join(
            id="j_ba",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="comp_b.top",
            edge_b_ref="comp_a.top",
        )
        manifest = ShapeManifest(components=(a, b), joins=(join_ab, join_ba))
        with pytest.raises(ValueError, match="Cycle detected"):
            derive_component_order(manifest)
