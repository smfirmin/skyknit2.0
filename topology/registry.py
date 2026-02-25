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
from typing import Optional

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

# (edge_type_a, edge_type_b, join_type)
CompatibilityKey = tuple[EdgeType, EdgeType, JoinType]


class TopologyRegistry:
    """
    Immutable registry of all topology lookup tables.

    Instantiate directly to use a custom data directory (e.g. in tests);
    otherwise use get_registry() for the module singleton.
    """

    def __init__(self, data_dir: Path = _DATA_DIR) -> None:
        self._data_dir = data_dir

        self.edge_types: dict[EdgeType, EdgeTypeEntry] = {}
        self.join_types: dict[JoinType, JoinTypeEntry] = {}
        self.compatibility: dict[CompatibilityKey, CompatibilityEntry] = {}
        self.defaults: dict[CompatibilityKey, dict] = {}
        self.arithmetic: dict[JoinType, ArithmeticEntry] = {}
        self.writer_dispatch: dict[JoinType, WriterDispatchEntry] = {}

        self._load_all()
        self._validate_cross_references()

    # ── Loading ────────────────────────────────────────────────────────────────

    def _load_yaml(self, filename: str) -> dict:
        path = self._data_dir / filename
        with open(path) as f:
            return yaml.safe_load(f)

    def _load_all(self) -> None:
        self._load_edge_types()
        self._load_join_types()
        self._load_compatibility()
        self._load_defaults()
        self._load_arithmetic()
        self._load_writer_dispatch()

    def _load_edge_types(self) -> None:
        data = self._load_yaml("edge_types.yaml")
        for entry in data["edge_types"]:
            et = EdgeType(entry["id"])
            self.edge_types[et] = EdgeTypeEntry(
                id=et,
                description=entry["description"].strip(),
                has_live_stitches=entry["has_live_stitches"],
                is_terminal=entry["is_terminal"],
                phase_constraint=entry["phase_constraint"],
                notes=entry.get("notes", "").strip(),
            )

    def _load_join_types(self) -> None:
        data = self._load_yaml("join_types.yaml")
        for entry in data["join_types"]:
            jt = JoinType(entry["id"])
            self.join_types[jt] = JoinTypeEntry(
                id=jt,
                description=entry["description"].strip(),
                symmetric=entry["symmetric"],
                directional=entry["directional"],
                owns_parameters=tuple(entry.get("owns_parameters", [])),
                construction_methods=tuple(entry.get("construction_methods", [])),
                notes=entry.get("notes", "").strip(),
            )

    def _load_compatibility(self) -> None:
        data = self._load_yaml("compatibility.yaml")
        for entry in data["entries"]:
            key: CompatibilityKey = (
                EdgeType(entry["edge_type_a"]),
                EdgeType(entry["edge_type_b"]),
                JoinType(entry["join_type"]),
            )
            self.compatibility[key] = CompatibilityEntry(
                edge_type_a=key[0],
                edge_type_b=key[1],
                join_type=key[2],
                result=CompatibilityResult(entry["result"]),
                condition_fn=entry.get("condition_fn"),
            )

    def _load_defaults(self) -> None:
        data = self._load_yaml("defaults.yaml")
        for entry in data["entries"]:
            key: CompatibilityKey = (
                EdgeType(entry["edge_type_a"]),
                EdgeType(entry["edge_type_b"]),
                JoinType(entry["join_type"]),
            )
            self.defaults[key] = entry.get("defaults", {})

    def _load_arithmetic(self) -> None:
        data = self._load_yaml("arithmetic_implications.yaml")
        for entry in data["entries"]:
            jt = JoinType(entry["join_type"])
            self.arithmetic[jt] = ArithmeticEntry(
                join_type=jt,
                implication=ArithmeticImplication(entry["implication"]),
                notes=entry.get("notes", "").strip(),
            )

    def _load_writer_dispatch(self) -> None:
        data = self._load_yaml("writer_dispatch.yaml")
        for entry in data["entries"]:
            jt = JoinType(entry["join_type"])
            self.writer_dispatch[jt] = WriterDispatchEntry(
                join_type=jt,
                rendering_mode=RenderingMode(entry["rendering_mode"]),
                template_key=entry["template_key"],
                directionality_note=entry["directionality_note"],
                conditional_template_key=entry.get("conditional_template_key"),
                notes=entry.get("notes", "").strip(),
            )

    # ── Cross-reference validation ─────────────────────────────────────────────

    def _validate_cross_references(self) -> None:
        """
        Run at startup. Raises ValueError listing all problems found if any
        lookup table entry references a type not defined in its master registry,
        or violates a structural invariant.
        """
        errors: list[str] = []

        # Compatibility table must reference only known edge and join types
        for (eta, etb, jt) in self.compatibility:
            if eta not in self.edge_types:
                errors.append(
                    f"compatibility references unknown edge_type_a: {eta!r}"
                )
            if etb not in self.edge_types:
                errors.append(
                    f"compatibility references unknown edge_type_b: {etb!r}"
                )
            if jt not in self.join_types:
                errors.append(
                    f"compatibility references unknown join_type: {jt!r}"
                )

        # Every CONDITIONAL entry must name a condition function
        for key, entry in self.compatibility.items():
            if (
                entry.result == CompatibilityResult.CONDITIONAL
                and not entry.condition_fn
            ):
                errors.append(
                    f"CONDITIONAL compatibility entry {key} is missing condition_fn"
                )

        # Every join type must have exactly one arithmetic implication
        for jt in self.join_types:
            if jt not in self.arithmetic:
                errors.append(
                    f"join type {jt!r} has no entry in arithmetic_implications"
                )

        # Every join type must have exactly one writer dispatch entry
        for jt in self.join_types:
            if jt not in self.writer_dispatch:
                errors.append(
                    f"join type {jt!r} has no entry in writer_dispatch"
                )

        # Defaults must reference only known join types
        for (_, _, jt) in self.defaults:
            if jt not in self.join_types:
                errors.append(
                    f"defaults references unknown join_type: {jt!r}"
                )

        # Terminal edge types must not appear in the compatibility table.
        # An is_terminal edge type has no join slot; any compatibility entry
        # that references one is a data error.
        terminal_types = {
            et for et, entry in self.edge_types.items() if entry.is_terminal
        }
        for (eta, etb, _) in self.compatibility:
            if eta in terminal_types:
                errors.append(
                    f"compatibility references terminal edge_type_a: {eta!r}"
                )
            if etb in terminal_types:
                errors.append(
                    f"compatibility references terminal edge_type_b: {etb!r}"
                )

        if errors:
            raise ValueError(
                "Topology registry cross-reference validation failed:\n"
                + "\n".join(f"  • {e}" for e in errors)
            )

    # ── Query API ──────────────────────────────────────────────────────────────

    def get_compatibility(
        self,
        edge_type_a: EdgeType,
        edge_type_b: EdgeType,
        join_type: JoinType,
    ) -> CompatibilityResult:
        """Return VALID, CONDITIONAL, or INVALID for the ordered triple."""
        key = (edge_type_a, edge_type_b, join_type)
        entry = self.compatibility.get(key)
        return entry.result if entry else CompatibilityResult.INVALID

    def get_condition_fn(
        self,
        edge_type_a: EdgeType,
        edge_type_b: EdgeType,
        join_type: JoinType,
    ) -> Optional[str]:
        """Return the condition function name for a CONDITIONAL entry, or None."""
        key = (edge_type_a, edge_type_b, join_type)
        entry = self.compatibility.get(key)
        return entry.condition_fn if entry else None

    def get_defaults(
        self,
        edge_type_a: EdgeType,
        edge_type_b: EdgeType,
        join_type: JoinType,
    ) -> dict:
        """Return default join-owned parameters for the given triple."""
        return dict(self.defaults.get((edge_type_a, edge_type_b, join_type), {}))

    def get_arithmetic(self, join_type: JoinType) -> ArithmeticImplication:
        return self.arithmetic[join_type].implication

    def get_writer_dispatch(self, join_type: JoinType) -> WriterDispatchEntry:
        return self.writer_dispatch[join_type]


# ── Module-level singleton ─────────────────────────────────────────────────────
#
# Initialized eagerly at import time so there is no lazy-init race condition
# in concurrent contexts. The registry is read-only after construction, so
# sharing it across threads is safe.

_registry: TopologyRegistry = TopologyRegistry()


def get_registry() -> TopologyRegistry:
    """Return the module-level registry singleton."""
    return _registry
