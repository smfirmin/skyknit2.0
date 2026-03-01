"""
Tests for runtime type objects: Edge, Join, CompatibilityKey, and frozen registry entries.

Covers:
  - Edge construction and mutability
  - Join construction, default parameters, and parameter independence
  - CompatibilityKey ordering and NamedTuple behaviour
  - Frozen registry entry dataclasses reject mutation
  - EdgeTypeEntry and JoinTypeEntry field values from known YAML data
"""

from types import MappingProxyType

import pytest

from skyknit.topology import (
    ArithmeticEntry,
    ArithmeticImplication,
    CompatibilityKey,
    CompatibilityResult,
    Edge,
    EdgeType,
    Join,
    JoinType,
    RenderingMode,
    get_registry,
)


@pytest.fixture(scope="module")
def registry():
    return get_registry()


# ── Edge runtime object ────────────────────────────────────────────────────────


class TestEdge:
    def test_construction_with_required_fields(self):
        edge = Edge(name="neck_cast_on", edge_type=EdgeType.CAST_ON)
        assert edge.name == "neck_cast_on"
        assert edge.edge_type == EdgeType.CAST_ON
        assert edge.join_ref is None

    def test_join_ref_defaults_to_none(self):
        edge = Edge(name="body_hem", edge_type=EdgeType.OPEN)
        assert edge.join_ref is None

    def test_join_ref_can_be_set(self):
        edge = Edge(name="yoke_underarm", edge_type=EdgeType.LIVE_STITCH, join_ref="underarm_join")
        assert edge.join_ref == "underarm_join"

    def test_edge_is_frozen(self):
        edge = Edge(name="original", edge_type=EdgeType.CAST_ON)
        with pytest.raises(AttributeError):
            edge.name = "updated"  # type: ignore[misc]

    def test_all_edge_types_accepted(self):
        for et in EdgeType:
            edge = Edge(name=f"test_{et.value}", edge_type=et)
            assert edge.edge_type == et


# ── Join runtime object ────────────────────────────────────────────────────────


class TestJoin:
    def test_construction_with_required_fields(self):
        join = Join(
            id="yoke_underarm",
            join_type=JoinType.CAST_ON_JOIN,
            edge_a_ref="yoke.underarm",
            edge_b_ref="sleeve.cast_on",
        )
        assert join.id == "yoke_underarm"
        assert join.join_type == JoinType.CAST_ON_JOIN
        assert join.edge_a_ref == "yoke.underarm"
        assert join.edge_b_ref == "sleeve.cast_on"
        assert join.parameters == {}

    def test_parameters_defaults_to_empty_dict(self):
        join = Join(
            id="j1",
            join_type=JoinType.CONTINUATION,
            edge_a_ref="a.edge",
            edge_b_ref="b.edge",
        )
        assert join.parameters == {}

    def test_parameters_can_be_provided(self):
        join = Join(
            id="j1",
            join_type=JoinType.CAST_ON_JOIN,
            edge_a_ref="yoke.underarm",
            edge_b_ref="sleeve.cast_on",
            parameters=MappingProxyType({"cast_on_count": 8, "cast_on_method": "backward_loop"}),
        )
        assert join.parameters["cast_on_count"] == 8
        assert join.parameters["cast_on_method"] == "backward_loop"

    def test_parameters_are_independent_between_instances(self):
        """Two joins with default parameters must not share the same proxy object."""
        join_a = Join(id="j1", join_type=JoinType.CONTINUATION, edge_a_ref="a.e", edge_b_ref="b.e")
        join_b = Join(id="j2", join_type=JoinType.CONTINUATION, edge_a_ref="c.e", edge_b_ref="d.e")
        assert join_a.parameters is not join_b.parameters

    def test_join_is_frozen(self):
        join = Join(
            id="original",
            join_type=JoinType.SEAM,
            edge_a_ref="a.bound_off",
            edge_b_ref="b.bound_off",
        )
        with pytest.raises(AttributeError):
            join.id = "updated"  # type: ignore[misc]

    def test_parameters_are_immutable(self):
        join = Join(
            id="j1",
            join_type=JoinType.PICKUP,
            edge_a_ref="body.neck",
            edge_b_ref="neckband.cast_on",
            parameters=MappingProxyType({"pickup_ratio": "3:4"}),
        )
        with pytest.raises(TypeError):
            join.parameters["pickup_direction"] = "left_to_right"  # type: ignore[index]

    def test_plain_dict_parameters_auto_converted(self):
        """Plain dicts passed at construction are promoted to MappingProxyType."""
        join = Join(
            id="j1",
            join_type=JoinType.CAST_ON_JOIN,
            edge_a_ref="a.e",
            edge_b_ref="b.e",
            parameters={"cast_on_count": 12},  # type: ignore[arg-type]
        )
        assert isinstance(join.parameters, MappingProxyType)
        assert join.parameters["cast_on_count"] == 12

    def test_all_join_types_accepted(self):
        for jt in JoinType:
            join = Join(id=f"j_{jt.value}", join_type=jt, edge_a_ref="a.e", edge_b_ref="b.e")
            assert join.join_type == jt

    def test_edge_ref_format(self):
        """edge_a_ref and edge_b_ref follow 'component.edge_name' convention."""
        join = Join(
            id="j1",
            join_type=JoinType.HELD_STITCH,
            edge_a_ref="yoke.sleeve_separation",
            edge_b_ref="sleeve.underarm",
        )
        assert "." in join.edge_a_ref
        assert "." in join.edge_b_ref


# ── CompatibilityKey ───────────────────────────────────────────────────────────


class TestCompatibilityKey:
    def test_construction_by_position(self):
        key = CompatibilityKey(EdgeType.LIVE_STITCH, EdgeType.CAST_ON, JoinType.CAST_ON_JOIN)
        assert key.edge_type_a == EdgeType.LIVE_STITCH
        assert key.edge_type_b == EdgeType.CAST_ON
        assert key.join_type == JoinType.CAST_ON_JOIN

    def test_construction_by_name(self):
        key = CompatibilityKey(
            edge_type_a=EdgeType.BOUND_OFF,
            edge_type_b=EdgeType.LIVE_STITCH,
            join_type=JoinType.PICKUP,
        )
        assert key.edge_type_a == EdgeType.BOUND_OFF
        assert key.edge_type_b == EdgeType.LIVE_STITCH
        assert key.join_type == JoinType.PICKUP

    def test_ordering_is_not_commutative(self):
        key_forward = CompatibilityKey(
            EdgeType.LIVE_STITCH, EdgeType.CAST_ON, JoinType.CAST_ON_JOIN
        )
        key_reverse = CompatibilityKey(
            EdgeType.CAST_ON, EdgeType.LIVE_STITCH, JoinType.CAST_ON_JOIN
        )
        assert key_forward != key_reverse

    def test_identical_keys_are_equal(self):
        key_a = CompatibilityKey(EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM)
        key_b = CompatibilityKey(EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM)
        assert key_a == key_b

    def test_key_is_hashable(self):
        key = CompatibilityKey(EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CONTINUATION)
        d = {key: "value"}
        assert d[key] == "value"

    def test_key_is_immutable(self):
        key = CompatibilityKey(EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.SEAM)
        with pytest.raises(AttributeError):
            key.edge_type_a = EdgeType.BOUND_OFF  # type: ignore[misc]

    def test_key_unpacks_as_tuple(self):
        key = CompatibilityKey(EdgeType.SELVEDGE, EdgeType.LIVE_STITCH, JoinType.PICKUP)
        eta, etb, jt = key
        assert eta == EdgeType.SELVEDGE
        assert etb == EdgeType.LIVE_STITCH
        assert jt == JoinType.PICKUP


# ── Frozen registry entry dataclasses ─────────────────────────────────────────


class TestFrozenEntries:
    def test_edge_type_entry_is_frozen(self, registry):
        entry = registry.edge_types[EdgeType.LIVE_STITCH]
        with pytest.raises((AttributeError, TypeError)):
            entry.description = "hacked"

    def test_join_type_entry_is_frozen(self, registry):
        entry = registry.join_types[JoinType.SEAM]
        with pytest.raises((AttributeError, TypeError)):
            entry.symmetric = False

    def test_compatibility_entry_is_frozen(self, registry):
        key = CompatibilityKey(EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CONTINUATION)
        entry = registry.compatibility[key]
        with pytest.raises((AttributeError, TypeError)):
            entry.result = CompatibilityResult.INVALID

    def test_arithmetic_entry_is_frozen(self, registry):
        entry = registry.arithmetic[JoinType.PICKUP]
        with pytest.raises((AttributeError, TypeError)):
            entry.implication = ArithmeticImplication.ONE_TO_ONE

    def test_writer_dispatch_entry_is_frozen(self, registry):
        entry = registry.writer_dispatch[JoinType.CONTINUATION]
        with pytest.raises((AttributeError, TypeError)):
            entry.rendering_mode = RenderingMode.HEADER_NOTE

    def test_direct_construction_of_frozen_entry(self):
        """Frozen entries can be constructed directly and are immediately immutable."""
        entry = ArithmeticEntry(
            join_type=JoinType.CONTINUATION, implication=ArithmeticImplication.ONE_TO_ONE
        )
        assert entry.join_type == JoinType.CONTINUATION
        with pytest.raises((AttributeError, TypeError)):
            entry.join_type = JoinType.SEAM  # type: ignore[misc]


# ── EdgeTypeEntry field values ─────────────────────────────────────────────────


class TestEdgeTypeEntryFields:
    @pytest.mark.parametrize(
        "et, has_live, is_terminal",
        [
            (EdgeType.CAST_ON, False, False),
            (EdgeType.LIVE_STITCH, True, False),
            (EdgeType.BOUND_OFF, False, False),
            (EdgeType.SELVEDGE, False, False),
            (EdgeType.OPEN, False, True),
        ],
    )
    def test_has_live_stitches_and_is_terminal(self, registry, et, has_live, is_terminal):
        entry = registry.edge_types[et]
        assert entry.has_live_stitches is has_live, (
            f"{et.value}: expected has_live_stitches={has_live}"
        )
        assert entry.is_terminal is is_terminal, f"{et.value}: expected is_terminal={is_terminal}"

    def test_only_live_stitch_has_live_stitches(self, registry):
        """LIVE_STITCH is the only edge type with a type-level live-stitch guarantee."""
        for et, entry in registry.edge_types.items():
            if et == EdgeType.LIVE_STITCH:
                assert entry.has_live_stitches is True
            else:
                assert entry.has_live_stitches is False

    def test_only_open_is_terminal(self, registry):
        for et, entry in registry.edge_types.items():
            if et == EdgeType.OPEN:
                assert entry.is_terminal is True
            else:
                assert entry.is_terminal is False

    @pytest.mark.parametrize(
        "et, phase",
        [
            (EdgeType.CAST_ON, "start"),
            (EdgeType.LIVE_STITCH, "any"),
            (EdgeType.BOUND_OFF, "end"),
            (EdgeType.SELVEDGE, "any"),
            (EdgeType.OPEN, "end"),
        ],
    )
    def test_phase_constraints(self, registry, et, phase):
        assert registry.edge_types[et].phase_constraint == phase


# ── JoinTypeEntry field values ─────────────────────────────────────────────────


class TestJoinTypeEntryFields:
    @pytest.mark.parametrize(
        "jt, symmetric, directional",
        [
            (JoinType.CONTINUATION, False, True),
            (JoinType.HELD_STITCH, False, True),
            (JoinType.CAST_ON_JOIN, False, True),
            (JoinType.PICKUP, False, True),
            (JoinType.SEAM, True, False),
        ],
    )
    def test_symmetric_and_directional(self, registry, jt, symmetric, directional):
        entry = registry.join_types[jt]
        assert entry.symmetric is symmetric, f"{jt.value}: expected symmetric={symmetric}"
        assert entry.directional is directional, f"{jt.value}: expected directional={directional}"

    def test_seam_is_only_symmetric_join(self, registry):
        for jt, entry in registry.join_types.items():
            if jt == JoinType.SEAM:
                assert entry.symmetric is True
            else:
                assert entry.symmetric is False

    def test_cast_on_join_owns_cast_on_parameters(self, registry):
        entry = registry.join_types[JoinType.CAST_ON_JOIN]
        assert "cast_on_count" in entry.owns_parameters
        assert "cast_on_method" in entry.owns_parameters

    def test_pickup_owns_pickup_parameters(self, registry):
        entry = registry.join_types[JoinType.PICKUP]
        assert "pickup_ratio" in entry.owns_parameters
        assert "pickup_direction" in entry.owns_parameters

    def test_seam_owns_seam_method(self, registry):
        entry = registry.join_types[JoinType.SEAM]
        assert "seam_method" in entry.owns_parameters

    def test_continuation_owns_no_parameters(self, registry):
        entry = registry.join_types[JoinType.CONTINUATION]
        assert entry.owns_parameters == ()

    def test_held_stitch_owns_no_parameters(self, registry):
        entry = registry.join_types[JoinType.HELD_STITCH]
        assert entry.owns_parameters == ()

    def test_owns_parameters_is_tuple(self, registry):
        for jt, entry in registry.join_types.items():
            assert isinstance(entry.owns_parameters, tuple), (
                f"{jt.value}: owns_parameters should be a tuple"
            )

    def test_construction_methods_is_tuple(self, registry):
        for jt, entry in registry.join_types.items():
            assert isinstance(entry.construction_methods, tuple), (
                f"{jt.value}: construction_methods should be a tuple"
            )

    def test_all_join_types_have_construction_methods(self, registry):
        for jt, entry in registry.join_types.items():
            assert len(entry.construction_methods) > 0, (
                f"{jt.value}: construction_methods must not be empty"
            )
