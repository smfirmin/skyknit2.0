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

    def test_public_types_in_all(self):
        """All public types, including CompatibilityKey, must appear in topology.__all__."""
        import topology

        for name in [
            "EdgeType",
            "JoinType",
            "CompatibilityResult",
            "ArithmeticImplication",
            "RenderingMode",
            "Edge",
            "Join",
            "EdgeTypeEntry",
            "JoinTypeEntry",
            "CompatibilityEntry",
            "ArithmeticEntry",
            "WriterDispatchEntry",
            "CompatibilityKey",
            "TopologyRegistry",
            "get_registry",
        ]:
            assert name in topology.__all__, f"{name!r} missing from topology.__all__"

    def test_all_edge_types_present(self, registry):
        for et in EdgeType:
            assert et in registry.edge_types, (
                f"EdgeType.{et.value} missing from edge_types registry"
            )

    def test_all_join_types_present(self, registry):
        for jt in JoinType:
            assert jt in registry.join_types, (
                f"JoinType.{jt.value} missing from join_types registry"
            )

    def test_all_join_types_have_arithmetic(self, registry):
        for jt in JoinType:
            assert jt in registry.arithmetic, f"JoinType.{jt.value} missing from arithmetic"

    def test_all_join_types_have_writer_dispatch(self, registry):
        for jt in JoinType:
            assert jt in registry.writer_dispatch, (
                f"JoinType.{jt.value} missing from writer_dispatch"
            )

    def test_edge_type_entries_have_descriptions(self, registry):
        for et, entry in registry.edge_types.items():
            assert entry.description, f"EdgeType.{et.value} has empty description"

    def test_join_type_entries_have_descriptions(self, registry):
        for jt, entry in registry.join_types.items():
            assert entry.description, f"JoinType.{jt.value} has empty description"


# ── Compatibility table ────────────────────────────────────────────────────────


class TestCompatibility:
    @pytest.mark.parametrize(
        "eta, etb, jt",
        [
            # All combinations that must be VALID in top-down sweater construction
            (EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
            (EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.HELD_STITCH),
            (EdgeType.LIVE_STITCH, EdgeType.CAST_ON, JoinType.CAST_ON_JOIN),
            (EdgeType.BOUND_OFF, EdgeType.LIVE_STITCH, JoinType.PICKUP),
            (EdgeType.SELVEDGE, EdgeType.LIVE_STITCH, JoinType.PICKUP),
            (EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM),
        ],
    )
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
        fn = registry.get_condition_fn(EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.SEAM)
        assert fn is not None and len(fn) > 0

    @pytest.mark.parametrize(
        "eta, etb, jt",
        [
            # Edges that cannot participate in these joins
            (EdgeType.CAST_ON, EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
            (EdgeType.BOUND_OFF, EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
            (EdgeType.OPEN, EdgeType.LIVE_STITCH, JoinType.CONTINUATION),
            (EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.CONTINUATION),
            (EdgeType.CAST_ON, EdgeType.CAST_ON, JoinType.SEAM),
            (EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.CAST_ON_JOIN),
            (EdgeType.OPEN, EdgeType.OPEN, JoinType.SEAM),
        ],
    )
    def test_known_invalid(self, registry, eta, etb, jt):
        result = registry.get_compatibility(eta, etb, jt)
        assert result == CompatibilityResult.INVALID, (
            f"Expected INVALID for ({eta.value}, {etb.value}, {jt.value}), got {result.value}"
        )

    def test_unknown_triple_returns_invalid(self, registry):
        """Any triple not in the table defaults to INVALID."""
        result = registry.get_compatibility(EdgeType.OPEN, EdgeType.OPEN, JoinType.CONTINUATION)
        assert result == CompatibilityResult.INVALID

    def test_open_is_terminal_and_absent_from_compatibility(self, registry):
        """OPEN is flagged is_terminal and must not appear in any compatibility entry."""
        assert registry.edge_types[EdgeType.OPEN].is_terminal is True
        for eta, etb, _ in registry.compatibility:
            assert eta != EdgeType.OPEN, "OPEN appeared as edge_type_a in compatibility"
            assert etb != EdgeType.OPEN, "OPEN appeared as edge_type_b in compatibility"

    def test_open_has_live_stitches_false(self, registry):
        """OPEN has_live_stitches must be false: liveness is instance-dependent, not a type guarantee."""
        assert registry.edge_types[EdgeType.OPEN].has_live_stitches is False

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
        fn = registry.get_condition_fn(EdgeType.OPEN, EdgeType.OPEN, JoinType.SEAM)
        assert fn is None


# ── Defaults ───────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_pickup_from_bound_off_has_ratio(self, registry):
        defaults = registry.get_defaults(EdgeType.BOUND_OFF, EdgeType.LIVE_STITCH, JoinType.PICKUP)
        assert "pickup_ratio" in defaults

    def test_pickup_from_selvedge_has_ratio(self, registry):
        defaults = registry.get_defaults(EdgeType.SELVEDGE, EdgeType.LIVE_STITCH, JoinType.PICKUP)
        assert "pickup_ratio" in defaults

    def test_seam_has_method(self, registry):
        defaults = registry.get_defaults(EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM)
        assert "seam_method" in defaults

    def test_three_needle_seam_has_method(self, registry):
        defaults = registry.get_defaults(EdgeType.LIVE_STITCH, EdgeType.LIVE_STITCH, JoinType.SEAM)
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
        defaults = registry.get_defaults(EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM)
        defaults["injected"] = "should not persist"
        clean = registry.get_defaults(EdgeType.BOUND_OFF, EdgeType.BOUND_OFF, JoinType.SEAM)
        assert "injected" not in clean


# ── Arithmetic implications ────────────────────────────────────────────────────


class TestArithmetic:
    @pytest.mark.parametrize(
        "jt, expected",
        [
            (JoinType.CONTINUATION, ArithmeticImplication.ONE_TO_ONE),
            (JoinType.HELD_STITCH, ArithmeticImplication.ONE_TO_ONE),
            (JoinType.CAST_ON_JOIN, ArithmeticImplication.ADDITIVE),
            (JoinType.PICKUP, ArithmeticImplication.RATIO),
            (JoinType.SEAM, ArithmeticImplication.STRUCTURAL),
        ],
    )
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

    def test_seam_has_conditional_template_key(self, registry):
        """SEAM must expose a conditional_template_key for three-needle bind-off."""
        entry = registry.get_writer_dispatch(JoinType.SEAM)
        assert entry.conditional_template_key == "three_needle_block"

    def test_non_conditional_join_types_have_no_conditional_template_key(self, registry):
        """Join types with no CONDITIONAL variant must not have a conditional_template_key."""
        for jt in (
            JoinType.CONTINUATION,
            JoinType.HELD_STITCH,
            JoinType.CAST_ON_JOIN,
            JoinType.PICKUP,
        ):
            entry = registry.get_writer_dispatch(jt)
            assert entry.conditional_template_key is None, (
                f"JoinType.{jt.value} unexpectedly has conditional_template_key"
            )


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
        with pytest.raises(ValueError):
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
        with pytest.raises(ValueError):
            TopologyRegistry(data_dir=data_dir)

    def test_terminal_edge_in_compatibility_raises(self, tmp_path):
        """A compatibility entry referencing a terminal edge type must fail at load."""
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        bad = data_dir / "compatibility.yaml"
        bad.write_text(
            bad.read_text()
            + (
                "\n  - edge_type_a: OPEN\n"
                "    edge_type_b: LIVE_STITCH\n"
                "    join_type: CONTINUATION\n"
                "    result: VALID\n"
            )
        )
        with pytest.raises(ValueError):
            TopologyRegistry(data_dir=data_dir)

    def test_bad_edge_type_in_defaults_raises(self, tmp_path):
        """A defaults entry referencing an unknown edge type must fail at load."""
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        bad = data_dir / "defaults.yaml"
        bad.write_text(
            bad.read_text()
            + (
                "\n  - edge_type_a: NONEXISTENT_EDGE\n"
                "    edge_type_b: LIVE_STITCH\n"
                "    join_type: PICKUP\n"
                "    defaults:\n"
                '      pickup_ratio: "3:4"\n'
            )
        )
        with pytest.raises(ValueError):
            TopologyRegistry(data_dir=data_dir)


# ── YAML loading error paths ───────────────────────────────────────────────────


class TestYAMLLoadingErrors:
    def test_missing_edge_types_file_raises(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)
        (data_dir / "edge_types.yaml").unlink()
        with pytest.raises(FileNotFoundError):
            TopologyRegistry(data_dir=data_dir)

    def test_missing_join_types_file_raises(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)
        (data_dir / "join_types.yaml").unlink()
        with pytest.raises(FileNotFoundError):
            TopologyRegistry(data_dir=data_dir)

    def test_missing_compatibility_file_raises(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)
        (data_dir / "compatibility.yaml").unlink()
        with pytest.raises(FileNotFoundError):
            TopologyRegistry(data_dir=data_dir)

    def test_missing_defaults_file_raises(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)
        (data_dir / "defaults.yaml").unlink()
        with pytest.raises(FileNotFoundError):
            TopologyRegistry(data_dir=data_dir)

    def test_missing_arithmetic_file_raises(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)
        (data_dir / "arithmetic_implications.yaml").unlink()
        with pytest.raises(FileNotFoundError):
            TopologyRegistry(data_dir=data_dir)

    def test_missing_writer_dispatch_file_raises(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)
        (data_dir / "writer_dispatch.yaml").unlink()
        with pytest.raises(FileNotFoundError):
            TopologyRegistry(data_dir=data_dir)

    def test_malformed_yaml_raises_value_error(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)
        (data_dir / "edge_types.yaml").write_text("entries: [\n  - id: BROKEN\n    bad: {unclosed")
        with pytest.raises(ValueError, match="Failed to parse"):
            TopologyRegistry(data_dir=data_dir)

    def test_invalid_edge_type_enum_in_yaml_raises(self, tmp_path):
        """An unrecognised enum value in YAML must raise at load time."""
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        bad = data_dir / "edge_types.yaml"
        bad.write_text(
            bad.read_text()
            + (
                "\n  - id: TOTALLY_INVALID\n"
                "    description: bad entry\n"
                "    has_live_stitches: false\n"
                "    is_terminal: false\n"
                "    phase_constraint: any\n"
            )
        )
        with pytest.raises(ValueError):
            TopologyRegistry(data_dir=data_dir)

    def test_invalid_join_type_enum_in_arithmetic_raises(self, tmp_path):
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        bad = data_dir / "arithmetic_implications.yaml"
        bad.write_text(
            bad.read_text() + "\n  - join_type: NONEXISTENT\n    implication: ONE_TO_ONE\n"
        )
        with pytest.raises(ValueError):
            TopologyRegistry(data_dir=data_dir)


# ── Join type completeness validation ─────────────────────────────────────────


class TestJoinTypeCompletenessValidation:
    def test_missing_arithmetic_entry_raises(self, tmp_path):
        """A join type with no arithmetic entry must fail cross-reference validation."""
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        # Rewrite arithmetic file with one join type missing
        original = (data_dir / "arithmetic_implications.yaml").read_text()
        lines = [line for line in original.splitlines(keepends=True) if "CONTINUATION" not in line]
        (data_dir / "arithmetic_implications.yaml").write_text("".join(lines))
        with pytest.raises(ValueError, match="arithmetic"):
            TopologyRegistry(data_dir=data_dir)

    def test_missing_writer_dispatch_entry_raises(self, tmp_path):
        """A join type with no writer dispatch entry must fail cross-reference validation."""
        data_dir = tmp_path / "data"
        shutil.copytree(_DATA_DIR, data_dir)

        original = (data_dir / "writer_dispatch.yaml").read_text()
        lines = [line for line in original.splitlines(keepends=True) if "CONTINUATION" not in line]
        (data_dir / "writer_dispatch.yaml").write_text("".join(lines))
        with pytest.raises(ValueError, match="writer_dispatch"):
            TopologyRegistry(data_dir=data_dir)


# ── Condition function global invariant ───────────────────────────────────────


class TestConditionFnInvariant:
    def test_all_conditional_entries_have_condition_fn(self, registry):
        """Every entry with result=CONDITIONAL must carry a non-empty condition_fn."""
        for key, entry in registry.compatibility.items():
            if entry.result == CompatibilityResult.CONDITIONAL:
                assert entry.condition_fn is not None and len(entry.condition_fn) > 0, (
                    f"CONDITIONAL entry {key} has no condition_fn"
                )

    def test_no_valid_entry_has_condition_fn(self, registry):
        """VALID entries must never carry a condition_fn."""
        for key, entry in registry.compatibility.items():
            if entry.result == CompatibilityResult.VALID:
                assert entry.condition_fn is None, (
                    f"VALID entry {key} unexpectedly has condition_fn={entry.condition_fn!r}"
                )

    def test_no_invalid_entry_has_condition_fn(self, registry):
        """INVALID entries must never carry a condition_fn."""
        for key, entry in registry.compatibility.items():
            if entry.result == CompatibilityResult.INVALID:
                assert entry.condition_fn is None, (
                    f"INVALID entry {key} unexpectedly has condition_fn={entry.condition_fn!r}"
                )

    def test_condition_fn_is_non_empty_string(self, registry):
        """condition_fn values must be non-empty strings, not empty string placeholders."""
        for key, entry in registry.compatibility.items():
            if entry.condition_fn is not None:
                assert isinstance(entry.condition_fn, str) and entry.condition_fn.strip(), (
                    f"condition_fn for {key} is blank or not a string"
                )


# ── Cross-table consistency ────────────────────────────────────────────────────


class TestCrossTableConsistency:
    def test_all_defaults_keys_reference_valid_types(self, registry):
        """Every key in the defaults table must use known EdgeType and JoinType values."""
        for key in registry.defaults:
            assert key.edge_type_a in registry.edge_types, (
                f"defaults key {key}: edge_type_a not in edge_types"
            )
            assert key.edge_type_b in registry.edge_types, (
                f"defaults key {key}: edge_type_b not in edge_types"
            )
            assert key.join_type in registry.join_types, (
                f"defaults key {key}: join_type not in join_types"
            )

    def test_all_arithmetic_keys_are_known_join_types(self, registry):
        for jt in registry.arithmetic:
            assert jt in registry.join_types

    def test_all_writer_dispatch_keys_are_known_join_types(self, registry):
        for jt in registry.writer_dispatch:
            assert jt in registry.join_types

    def test_conditional_template_key_only_when_conditional_variant_exists(self, registry):
        """A join type should only expose conditional_template_key if a CONDITIONAL
        compatibility entry exists for that join type."""
        join_types_with_conditional = {
            key.join_type
            for key, entry in registry.compatibility.items()
            if entry.result == CompatibilityResult.CONDITIONAL
        }
        for jt, entry in registry.writer_dispatch.items():
            if entry.conditional_template_key is not None:
                assert jt in join_types_with_conditional, (
                    f"{jt.value}: has conditional_template_key but no CONDITIONAL "
                    "compatibility entry"
                )

    def test_registry_tables_are_mapping_proxies(self, registry):
        """All public table attributes must be MappingProxyType (immutable)."""
        from types import MappingProxyType

        assert isinstance(registry.edge_types, MappingProxyType)
        assert isinstance(registry.join_types, MappingProxyType)
        assert isinstance(registry.compatibility, MappingProxyType)
        assert isinstance(registry.defaults, MappingProxyType)
        assert isinstance(registry.arithmetic, MappingProxyType)
        assert isinstance(registry.writer_dispatch, MappingProxyType)

    def test_registry_tables_are_not_directly_mutable(self, registry):
        """MappingProxyType tables must reject direct key assignment."""
        import pytest

        with pytest.raises(TypeError):
            registry.edge_types[EdgeType.OPEN] = None
