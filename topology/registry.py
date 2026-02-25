"""
Topology registry: loads all lookup tables from YAML at startup, validates
cross-references, and exposes a read-only query API.

The registry is a module-level singleton; call get_registry() to obtain it.
All tables are loaded and validated once at import time. Nothing writes to
the registry after startup.

──────────────────────────────────────────────────────────────────────────────
condition_fn contract
──────────────────────────────────────────────────────────────────────────────
CONDITIONAL compatibility entries carry a condition_fn field: the name of a
Python callable that the Geometric Validator must resolve and invoke to
determine whether a specific join instance satisfies the constraint.

Expected signature:
    def <condition_fn>(join: topology.types.Join,
                       manifest: planner.ShapeManifest) -> bool:
        ...

The function must be pure (no side effects), deterministic, and raise
ValueError (not return False) if the join parameters are structurally invalid
(e.g. missing required keys). A return value of True means the join passes;
False means it fails the constraint.

Condition functions are registered in geometry_validator.conditions and looked
up by name at validation time. The registry only stores the name string; it
does not hold a reference to the callable.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, NamedTuple, Optional, cast

import yaml

from .types import (
    ArithmeticEntry,
    ArithmeticImplication,
    CompatibilityEntry,
    CompatibilityResult,
    EdgeType,
    EdgeTypeEntry,
    JoinType,
    JoinTypeEntry,
    RenderingMode,
    WriterDispatchEntry,
)

_DATA_DIR = Path(__file__).parent / "data"


class CompatibilityKey(NamedTuple):
    """
    Ordered triple used as the key in the compatibility and defaults tables.

    Ordering is significant and non-commutative: edge_type_a is from the
    upstream/source component; edge_type_b is from the downstream/receiving
    component. Using a NamedTuple enforces field names at construction sites
    and prevents silent key-transposition bugs.
    """

    edge_type_a: EdgeType
    edge_type_b: EdgeType
    join_type: JoinType


class TopologyRegistry:
    """
    Read-only registry of all topology lookup tables.

    All public dict attributes are wrapped in MappingProxyType after loading
    and are immutable for the lifetime of the registry instance.

    Instantiate directly to use a custom data directory (e.g. in tests);
    otherwise use get_registry() for the module singleton.
    """

    def __init__(self, data_dir: Path = _DATA_DIR) -> None:
        self._data_dir = data_dir

        # Type annotations only; actual assignment happens in _load_*
        self.edge_types: MappingProxyType[EdgeType, EdgeTypeEntry]
        self.join_types: MappingProxyType[JoinType, JoinTypeEntry]
        self.compatibility: MappingProxyType[CompatibilityKey, CompatibilityEntry]
        self.defaults: MappingProxyType[CompatibilityKey, dict[str, Any]]
        self.arithmetic: MappingProxyType[JoinType, ArithmeticEntry]
        self.writer_dispatch: MappingProxyType[JoinType, WriterDispatchEntry]

        self._load_all()
        self._validate_cross_references()

    # ── Loading ────────────────────────────────────────────────────────────────

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = self._data_dir / filename
        try:
            with open(path) as f:
                return cast(dict[str, Any], yaml.safe_load(f))
        except FileNotFoundError:
            raise FileNotFoundError(f"Topology data file not found: {path}") from None
        except yaml.YAMLError as exc:
            raise ValueError(f"Failed to parse topology data file {path}: {exc}") from exc

    def _load_all(self) -> None:
        self._load_edge_types()
        self._load_join_types()
        self._load_compatibility()
        self._load_defaults()
        self._load_arithmetic()
        self._load_writer_dispatch()

    def _load_edge_types(self) -> None:
        data = self._load_yaml("edge_types.yaml")
        result: dict[EdgeType, EdgeTypeEntry] = {}
        for entry in data["entries"]:
            et = EdgeType(entry["id"])
            result[et] = EdgeTypeEntry(
                id=et,
                description=entry["description"].strip(),
                has_live_stitches=entry["has_live_stitches"],
                is_terminal=entry["is_terminal"],
                phase_constraint=entry["phase_constraint"],
                notes=entry.get("notes", "").strip(),
            )
        self.edge_types = MappingProxyType(result)

    def _load_join_types(self) -> None:
        data = self._load_yaml("join_types.yaml")
        result: dict[JoinType, JoinTypeEntry] = {}
        for entry in data["entries"]:
            jt = JoinType(entry["id"])
            result[jt] = JoinTypeEntry(
                id=jt,
                description=entry["description"].strip(),
                symmetric=entry["symmetric"],
                directional=entry["directional"],
                owns_parameters=tuple(entry.get("owns_parameters", [])),
                construction_methods=tuple(entry.get("construction_methods", [])),
                notes=entry.get("notes", "").strip(),
            )
        self.join_types = MappingProxyType(result)

    def _load_compatibility(self) -> None:
        data = self._load_yaml("compatibility.yaml")
        result: dict[CompatibilityKey, CompatibilityEntry] = {}
        for entry in data["entries"]:
            key = CompatibilityKey(
                edge_type_a=EdgeType(entry["edge_type_a"]),
                edge_type_b=EdgeType(entry["edge_type_b"]),
                join_type=JoinType(entry["join_type"]),
            )
            result[key] = CompatibilityEntry(
                edge_type_a=key.edge_type_a,
                edge_type_b=key.edge_type_b,
                join_type=key.join_type,
                result=CompatibilityResult(entry["result"]),
                condition_fn=entry.get("condition_fn"),
            )
        self.compatibility = MappingProxyType(result)

    def _load_defaults(self) -> None:
        data = self._load_yaml("defaults.yaml")
        result: dict[CompatibilityKey, dict[str, Any]] = {}
        for entry in data["entries"]:
            key = CompatibilityKey(
                edge_type_a=EdgeType(entry["edge_type_a"]),
                edge_type_b=EdgeType(entry["edge_type_b"]),
                join_type=JoinType(entry["join_type"]),
            )
            result[key] = entry.get("defaults", {})
        self.defaults = MappingProxyType(result)

    def _load_arithmetic(self) -> None:
        data = self._load_yaml("arithmetic_implications.yaml")
        result: dict[JoinType, ArithmeticEntry] = {}
        for entry in data["entries"]:
            jt = JoinType(entry["join_type"])
            result[jt] = ArithmeticEntry(
                join_type=jt,
                implication=ArithmeticImplication(entry["implication"]),
                notes=entry.get("notes", "").strip(),
            )
        self.arithmetic = MappingProxyType(result)

    def _load_writer_dispatch(self) -> None:
        data = self._load_yaml("writer_dispatch.yaml")
        result: dict[JoinType, WriterDispatchEntry] = {}
        for entry in data["entries"]:
            jt = JoinType(entry["join_type"])
            result[jt] = WriterDispatchEntry(
                join_type=jt,
                rendering_mode=RenderingMode(entry["rendering_mode"]),
                template_key=entry["template_key"],
                directionality_note=entry["directionality_note"],
                conditional_template_key=entry.get("conditional_template_key"),
                notes=entry.get("notes", "").strip(),
            )
        self.writer_dispatch = MappingProxyType(result)

    # ── Cross-reference validation ─────────────────────────────────────────────

    def _validate_cross_references(self) -> None:
        """
        Run at startup. Raises ValueError listing all problems found if any
        lookup table entry references a type not defined in its master registry,
        or violates a structural invariant.
        """
        errors: list[str] = []
        self._check_compatibility_table(errors)
        self._check_join_type_completeness(errors)
        self._check_defaults_references(errors)
        if errors:
            raise ValueError(
                "Topology registry cross-reference validation failed:\n"
                + "\n".join(f"  • {e}" for e in errors)
            )

    def _check_compatibility_table(self, errors: list[str]) -> None:
        """Validate all compatibility entries in a single pass.

        Checks: (a) referenced edge/join types exist, (b) referenced edge types
        are not terminal, (c) CONDITIONAL entries have a condition_fn.
        """
        terminal_types = {et for et, entry in self.edge_types.items() if entry.is_terminal}
        for key, entry in self.compatibility.items():
            prefix = (
                f"compatibility entry "
                f"({key.edge_type_a.value}, {key.edge_type_b.value}, {key.join_type.value})"
            )
            if key.edge_type_a not in self.edge_types:
                errors.append(
                    f"{prefix}: edge_type_a {key.edge_type_a!r} is not defined in edge_types"
                )
            elif key.edge_type_a in terminal_types:
                errors.append(
                    f"{prefix}: edge_type_a {key.edge_type_a!r} is terminal and cannot appear in compatibility"
                )
            if key.edge_type_b not in self.edge_types:
                errors.append(
                    f"{prefix}: edge_type_b {key.edge_type_b!r} is not defined in edge_types"
                )
            elif key.edge_type_b in terminal_types:
                errors.append(
                    f"{prefix}: edge_type_b {key.edge_type_b!r} is terminal and cannot appear in compatibility"
                )
            if key.join_type not in self.join_types:
                errors.append(f"{prefix}: join_type {key.join_type!r} is not defined in join_types")
            if entry.result == CompatibilityResult.CONDITIONAL and not entry.condition_fn:
                errors.append(f"{prefix}: result is CONDITIONAL but condition_fn is not set")

    def _check_join_type_completeness(self, errors: list[str]) -> None:
        """Every join type must have exactly one arithmetic and one writer dispatch entry."""
        for jt in self.join_types:
            if jt not in self.arithmetic:
                errors.append(f"join_types entry {jt!r}: no entry in arithmetic_implications")
            if jt not in self.writer_dispatch:
                errors.append(f"join_types entry {jt!r}: no entry in writer_dispatch")

    def _check_defaults_references(self, errors: list[str]) -> None:
        """Defaults table must reference only known edge and join types."""
        for key in self.defaults:
            prefix = (
                f"defaults entry "
                f"({key.edge_type_a.value}, {key.edge_type_b.value}, {key.join_type.value})"
            )
            if key.edge_type_a not in self.edge_types:
                errors.append(
                    f"{prefix}: edge_type_a {key.edge_type_a!r} is not defined in edge_types"
                )
            if key.edge_type_b not in self.edge_types:
                errors.append(
                    f"{prefix}: edge_type_b {key.edge_type_b!r} is not defined in edge_types"
                )
            if key.join_type not in self.join_types:
                errors.append(f"{prefix}: join_type {key.join_type!r} is not defined in join_types")

    # ── Query API ──────────────────────────────────────────────────────────────

    def get_compatibility(
        self,
        edge_type_a: EdgeType,
        edge_type_b: EdgeType,
        join_type: JoinType,
    ) -> CompatibilityResult:
        """Return VALID, CONDITIONAL, or INVALID for the ordered triple."""
        key = CompatibilityKey(edge_type_a, edge_type_b, join_type)
        entry = self.compatibility.get(key)
        return entry.result if entry else CompatibilityResult.INVALID

    def get_condition_fn(
        self,
        edge_type_a: EdgeType,
        edge_type_b: EdgeType,
        join_type: JoinType,
    ) -> Optional[str]:
        """Return the condition function name for a CONDITIONAL entry, or None."""
        key = CompatibilityKey(edge_type_a, edge_type_b, join_type)
        entry = self.compatibility.get(key)
        return entry.condition_fn if entry else None

    def get_defaults(
        self,
        edge_type_a: EdgeType,
        edge_type_b: EdgeType,
        join_type: JoinType,
    ) -> dict[str, Any]:
        """Return a copy of default join-owned parameters for the given triple."""
        return dict(self.defaults.get(CompatibilityKey(edge_type_a, edge_type_b, join_type), {}))

    def get_arithmetic(self, join_type: JoinType) -> ArithmeticImplication:
        """Return the arithmetic implication for the given join type.

        Raises KeyError if the join type has no arithmetic entry. The
        cross-reference validation guarantees all JoinType enum values have
        entries after construction.
        """
        try:
            return self.arithmetic[join_type].implication
        except KeyError:
            raise KeyError(f"No arithmetic entry for join type {join_type!r}") from None

    def get_writer_dispatch(self, join_type: JoinType) -> WriterDispatchEntry:
        """Return the writer dispatch entry for the given join type.

        Raises KeyError if the join type has no writer dispatch entry. The
        cross-reference validation guarantees all JoinType enum values have
        entries after construction.
        """
        try:
            return self.writer_dispatch[join_type]
        except KeyError:
            raise KeyError(f"No writer dispatch entry for join type {join_type!r}") from None


# ── Module-level singleton ─────────────────────────────────────────────────────
#
# Initialized eagerly at import time so there is no lazy-init race condition
# in concurrent contexts. The registry is read-only after construction, so
# sharing it across threads is safe.

_registry: TopologyRegistry = TopologyRegistry()


def get_registry() -> TopologyRegistry:
    """Return the module-level registry singleton."""
    return _registry
