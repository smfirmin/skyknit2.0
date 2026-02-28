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

from schemas.constraint import ConstraintObject
from schemas.ir import ComponentIR
from schemas.manifest import ComponentSpec, Handedness
from topology.types import Join
from fillers.ir_builder import build_component_ir, mirror_component_ir
from fillers.resolver import resolve_stitch_counts


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

    Raises ValueError if any required stitch count cannot be resolved.
    """

    def fill(self, filler_input: FillerInput) -> FillerOutput:
        spec = filler_input.component_spec
        constraint = filler_input.constraint
        handedness = filler_input.handedness

        resolved = resolve_stitch_counts(spec, constraint)

        # Convert None → error: DeterministicFiller cannot escalate
        for edge_name, count in resolved.items():
            if count is None:
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
