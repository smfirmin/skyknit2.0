"""
StitchFiller protocol and DeterministicFiller implementation.

StitchFiller is the interface that all filler implementations must satisfy.
FillerInput and FillerOutput are the typed data contracts.

DeterministicFiller uses only the deterministic tools layer (resolver +
ir_builder) — no LLM calls.  It is suitable for simple geometric shapes and
is the primary filler used in testing.

Future implementations (e.g. LLMFiller) will satisfy the same protocol and
can be swapped in without changing the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from fillers.ir_builder import build_component_ir
from fillers.resolver import resolve_stitch_counts
from schemas.constraint import ConstraintObject
from schemas.ir import ComponentIR
from schemas.manifest import ComponentSpec, Handedness
from topology.types import EdgeType, Join

# Edge types that must resolve to a stitch count; all others (SELVEDGE, OPEN)
# are lateral/terminal and naturally produce None from the resolver.
_DIMENSION_BEARING: frozenset[EdgeType] = frozenset(
    {EdgeType.CAST_ON, EdgeType.LIVE_STITCH, EdgeType.BOUND_OFF}
)


@dataclass(frozen=True)
class FillerInput:
    """Everything a StitchFiller needs to produce a ComponentIR."""

    component_spec: ComponentSpec
    constraint: ConstraintObject
    joins: tuple[Join, ...]
    handedness: Handedness


@dataclass(frozen=True)
class FillerOutput:
    """The result of a StitchFiller.fill() call."""

    ir: ComponentIR
    resolved_counts: dict[str, int | None]


@runtime_checkable
class StitchFiller(Protocol):
    """
    Protocol that all Stitch Filler implementations must satisfy.

    A StitchFiller takes a FillerInput and returns a FillerOutput.
    Implementations may call the LLM, use only deterministic tools, or
    combine both — callers are agnostic.
    """

    def fill(self, filler_input: FillerInput) -> FillerOutput:
        """Produce a ComponentIR and resolved stitch counts for one component."""
        ...


class DeterministicFiller:
    """
    Stitch Filler that uses only deterministic tools — no LLM.

    Suitable for simple CYLINDER, TRAPEZOID, and RECTANGLE shapes where all
    stitch counts can be resolved directly from physical dimensions.

    SELVEDGE and OPEN edges are lateral/terminal and do not carry stitch counts;
    None for those edges is silently accepted.  None for dimension-bearing edge
    types (CAST_ON, LIVE_STITCH, BOUND_OFF) raises ValueError — the filler
    cannot escalate to an LLM.
    """

    def fill(self, filler_input: FillerInput) -> FillerOutput:
        spec = filler_input.component_spec
        constraint = filler_input.constraint
        handedness = filler_input.handedness

        resolved = resolve_stitch_counts(spec, constraint)

        # Only raise for edges that should carry stitch counts
        edge_types = {e.name: e.edge_type for e in spec.edges}
        for edge_name, count in resolved.items():
            if count is None and edge_types.get(edge_name) in _DIMENSION_BEARING:
                raise ValueError(
                    f"DeterministicFiller could not resolve stitch count for "
                    f"edge '{edge_name}' of component '{spec.name}'"
                )

        counts: dict[str, int] = {k: v for k, v in resolved.items() if v is not None}

        ir = build_component_ir(
            component_spec=spec,
            stitch_counts=counts,
            constraint=constraint,
            joins=list(filler_input.joins),
            handedness=handedness,
        )

        return FillerOutput(ir=ir, resolved_counts=resolved)
