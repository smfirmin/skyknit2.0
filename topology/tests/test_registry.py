"""
Tests for the topology registry.

Covers:
  - All YAML tables load without error
  - Every enum value has a registry entry
  - Cross-reference invariants hold
  - Specific known-valid combinations return VALID
  - Specific known-invalid combinations return INVALID
  - CONDITIONAL entries have a condition_fn
  - Key ordering is enforced (not commutative)
  - Defaults, arithmetic, and writer dispatch return expected values
  - Corrupted data raises at load time (not silently at query time)
"""

import shutil
from pathlib import Path

import pytest

from topology import (
    ArithmeticImplication,
    CompatibilityResult,
    EdgeType,
    JoinType,
    RenderingMode,
    get_registry,
)
from topology.registry import TopologyRegistry

_DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def registry():
    return get_registry()


# ── Registry loads ─────────────────────────────────────────────────────────────


class TestRegistryLoads:
    def test_loads_without_error(self, registry):
        assert registry is not None

    def test_all_edge_types_present(self, registry):
        for et in EdgeType:
            assert et in registry.edge_types, f"EdgeType.{et.value} missing from edge_types registry"

    def test_all_join_types_present(self, registry):
        for jt in JoinType:
            assert jt in registry.join_types, f"JoinType.{jt.value} missing from join_types registry"

    def test_all_join_types_have_arithmetic(self, registry):
        for jt in JoinType:
            assert jt in registry.arithmetic, f"JoinType.{jt.value} missing from arithmetic"

    def test_all_join_types_have_writer_dispatch(self, registry):
        for jt in JoinType:
            assert jt in registry.writer_dispatch, f"JoinType.{jt.value} missing from writer_dispatch"

    def test_edge_type_entries_have_descriptions(self, registry):
        for et, entry in registry.edge_types.items():
            assert entry.description, f"EdgeType.{et.value} has empty description"

    def test_join_type_entries_have_descriptions(self, registry):
        for jt, entry in registry.join_types.items():
            assert entry.description, f"JoinType.{jt.value} has empty description"


# ── Compatibility table ────────────────────────────────────────────────────────


class TestCompatibility:

    @pytest.mark.parametrize("eta, etb, jt", [
        # All combinations that must be VALID in top-down sweater construction
        (EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
        (EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.HELD_STITCH),
        (EdgeType.LIVE_STITCH, EdgeType.CAST_ON,     JoinType.CAST_ON_JOIN),
        (EdgeType.BOUND_OFF,   EdgeType.LIVE_STITCH, JoinType.PICKUP),
        (EdgeType.PICKUP,      EdgeType.LIVE_STITCH, JoinType.PICKUP),
        (EdgeType.BOUND_OFF,   EdgeType.BOUND_OFF,   JoinType.SEAM),
    ])
    def test_known_valid(self, registry, eta, etb, jt):
        result = registry.get_compatibility(eta, etb, jt)
        assert result == CompatibilityResult.VALID, (
            f"Expected VALID for ({eta.value}, {etb.value}, {jt.value}), got {result.value}"
        )

    def test_live_live_seam_is_conditional(self, registry):
        """Three-needle bind-off: LIVE_STITCH × LIVE_STITCH → SEAM is CONDITIONAL."""
        result = registry.get_compatibility(
            EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.SEAM
        )
        assert result == CompatibilityResult.CONDITIONAL

    def test_conditional_has_condition_fn(self, registry):
        fn = registry.get_condition_fn(
            EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.SEAM
        )
        assert fn is not None and len(fn) > 0

    @pytest.mark.parametrize("eta, etb, jt", [
        # Edges that cannot participate in these joins
        (EdgeType.CAST_ON,     EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
        (EdgeType.BOUND_OFF,   EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
        (EdgeType.OPEN,        EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
        (EdgeType.BOUND_OFF,   EdgeType.BOUND_OFF,   JoinType.CONTINUATION),
        (EdgeType.CAST_ON,     EdgeType.CAST_ON,     JoinType.SEAM),
        (EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CAST_ON_JOIN),
        (EdgeType.OPEN,        EdgeType.OPEN,         JoinType.SEAM),
    ])
    def test_known_invalid(self, registry, eta, etb, jt):
        result = registry.get_compatibility(eta, etb, jt)
        assert result == CompatibilityResult.INVALID, (
            f"Expected INVALID for ({eta.value}, {etb.value}, {jt.value}), got {result.value}"
        )

    def test_unknown_triple_returns_invalid(self, registry):
        """Any triple not in the table defaults to INVALID."""
        result = registry.get_compatibility(
            EdgeType.OPEN, EdgeType.OPEN, JoinType.CONTINUATION
        )
        assert result == CompatibilityResult.INVALID

    def test_key_is_ordered_not_commutative(self, registry):
        """(LIVE_STITCH, CAST_ON, CAST_ON_JOIN) is VALID; the reverse is INVALID."""
        forward = registry.get_compatibility(
            EdgeType.LIVE_STITCH, EdgeType.CAST_ON, JoinType.CAST_ON_JOIN
        )
        reverse = registry.get_compatibility(
            EdgeType.CAST_ON, EdgeType.LIVE_STITCH, JoinType.CAST_ON_JOIN
        )
        assert forward == CompatibilityResult.VALID
        assert reverse == CompatibilityResult.INVALID

    def test_condition_fn_none_for_valid_entry(self, registry):
        """VALID entries should not have a condition_fn."""
        fn = registry.get_condition_fn(
            EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CONTINUATION
        )
        assert fn is None

    def test_condition_fn_none_for_missing_entry(self, registry):
        fn = registry.get_condition_fn(
            EdgeType.OPEN, EdgeType.OPEN, JoinType.SEAM
        )
        assert fn is None


# ── Defaults ───────────────────────────────────────────────────────────────────


class TestDefaults:

    def test_pickup_from_bound_off_has_ratio(self, registry):
        defaults = registry.get_defaults(
            EdgeType.BOUND_OFF, EdgeType.LIVE_STITCH, JoinType.PICKUP
        )
        assert "pickup_ratio" in defaults

    def test_pickup_from_selvedge_has_ratio(self, registry):
        defaults = registry.get_defaults(
            EdgeType.PICKUP, EdgeType.LIVE_STITCH, JoinType.PICKUP
        )
        assert "pickup_ratio" in defaults

    def test_seam_has_method(self, registry):
        defaults = registry.get_defaults(
            EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM
        )
        assert "seam_method" in defaults

    def test_three_needle_seam_has_method(self, registry):
        defaults = registry.get_defaults(
            EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.SEAM
        )
        assert "seam_method" in defaults
        assert defaults["seam_method"] == "three_needle_bind_off"

    def test_cast_on_join_has_method(self, registry):
        defaults = registry.get_defaults(
            EdgeType.LIVE_STITCH, EdgeType.CAST_ON, JoinType.CAST_ON_JOIN
        )
        assert "cast_on_method" in defaults

    def test_cast_on_count_is_null(self, registry):
        """cast_on_count has no safe default and must always be set by the Planner."""
        defaults = registry.get_defaults(
            EdgeType.LIVE_STITCH, EdgeType.CAST_ON, JoinType.CAST_ON_JOIN
        )
        assert "cast_on_count" in defaults
        assert defaults["cast_on_count"] is None

    def test_continuation_has_no_defaults(self, registry):
        defaults = registry.get_defaults(
            EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CONTINUATION
        )
        assert defaults == {}

    def test_get_defaults_returns_copy(self, registry):
        """Mutating the returned dict must not affect the registry."""
        defaults = registry.get_defaults(
            EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM
        )
        defaults["injected"] = "should not persist"
        clean = registry.get_defaults(
            EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM
        )
        assert "injected" not in clean


# ── Arithmetic implications ────────────────────────────────────────────────────


class TestArithmetic:

    @pytest.mark.parametrize("jt, expected", [
        (JoinType.CONTINUATION, ArithmeticImplication.ONE_TO_ONE),
        (JoinType.HELD_STITCH,  ArithmeticImplication.ONE_TO_ONE),
        (JoinType.CAST_ON_JOIN, ArithmeticImplication.ADDITIVE),
        (JoinType.PICKUP,       ArithmeticImplication.RATIO),
        (JoinType.SEAM,         ArithmeticImplication.STRUCTURAL),
    ])
    def test_arithmetic_implications(self, registry, jt, expected):
        assert registry.get_arithmetic(jt) == expected


# ── Writer dispatch ────────────────────────────────────────────────────────────


class TestWriterDispatch:

    def test_continuation_is_inline(self, registry):
        entry = registry.get_writer_dispatch(JoinType.CONTINUATION)
        assert entry.rendering_mode == RenderingMode.INLINE

    def test_held_stitch_is_instruction(self, registry):
        entry = registry.get_writer_dispatch(JoinType.HELD_STITCH)
        assert entry.rendering_mode == RenderingMode.INSTRUCTION

    def test_cast_on_join_is_instruction(self, registry):
        entry = registry.get_writer_dispatch(JoinType.CAST_ON_JOIN)
        assert entry.rendering_mode == RenderingMode.INSTRUCTION

    def test_pickup_is_instruction(self, registry):
        entry = registry.get_writer_dispatch(JoinType.PICKUP)
        assert entry.rendering_mode == RenderingMode.INSTRUCTION

    def test_seam_is_header_note(self, registry):
        entry = registry.get_writer_dispatch(JoinType.SEAM)
        assert entry.rendering_mode == RenderingMode.HEADER_NOTE

    def test_held_stitch_has_directionality_note(self, registry):
        entry = registry.get_writer_dispatch(JoinType.HELD_STITCH)
        assert entry.directionality_note is True

    def test_continuation_has_no_directionality_note(self, registry):
        entry = registry.get_writer_dispatch(JoinType.CONTINUATION)
        assert entry.directionality_note is False

    def test_all_have_template_keys(self, registry):
        for jt in JoinType:
            entry = registry.get_writer_dispatch(jt)
            assert entry.template_key, f"JoinType.{jt.value} has empty template_key"


# ── Cross-reference validation at load time ────────────────────────────────────


class TestCrossReferenceValidation:

    def test_bad_join_type_in_compatibility_raises(self, tmp_path):
        """A compatibility entry referencing a nonexistent join type must fail at load."""
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        bad = data_dir / "compatibility.yaml"
        bad.write_text(
            bad.read_text()
            + (
                "\n  - edge_type_a: LIVE_STITCH\n"
                "    edge_type_b: LIVE_STITCH\n"
                "    join_type: NONEXISTENT_TYPE\n"
                "    result: VALID\n"
            )
        )
        with pytest.raises((ValueError, Exception)):
            TopologyRegistry(data_dir=data_dir)

    def test_conditional_without_condition_fn_raises(self, tmp_path):
        """A CONDITIONAL entry missing condition_fn must fail at load."""
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        bad = data_dir / "compatibility.yaml"
        bad.write_text(
            bad.read_text()
            + (
                "\n  - edge_type_a: BOUND_OFF\n"
                "    edge_type_b: BOUND_OFF\n"
                "    join_type: PICKUP\n"
                "    result: CONDITIONAL\n"
                # condition_fn deliberately omitted
            )
        )
        with pytest.raises((ValueError, Exception)):
            TopologyRegistry(data_dir=data_dir)
