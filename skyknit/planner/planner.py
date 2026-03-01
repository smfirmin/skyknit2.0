"""
Planner protocol, data contracts, and DeterministicPlanner implementation.

The Planner converts:
  GarmentSpec + ProportionSpec + body measurements
    → PlannerOutput (component_list + ShapeManifest)

Two-stage semantics:
  Stage 1 — component_list is available immediately (unblocks Fabric Module)
  Stage 2 — manifest is fully assembled (enables Stitch Fillers + Validator)

DeterministicPlanner uses only deterministic tools (no LLM).  A future
LLMPlanner will implement the same Planner protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from skyknit.planner.manifest_builder import build_shape_manifest
from skyknit.schemas.garment import GarmentSpec
from skyknit.schemas.manifest import ShapeManifest
from skyknit.schemas.proportion import ProportionSpec


@dataclass(frozen=True)
class PlannerInput:
    """Input bundle for the Planner."""

    garment_spec: GarmentSpec
    proportion_spec: ProportionSpec
    measurements: dict[str, float]  # open dict; keys are garment-type-specific, all in mm


@dataclass(frozen=True)
class PlannerOutput:
    """Output of the Planner — both pipeline stages."""

    component_list: list[str]  # stage 1: ordered component names; unblocks Fabric Module
    manifest: ShapeManifest  # stage 2: full topology with typed edges and Join objects


@runtime_checkable
class Planner(Protocol):
    """Protocol for all Planner implementations (deterministic, LLM, hybrid)."""

    def plan(self, planner_input: PlannerInput) -> PlannerOutput: ...


class DeterministicPlanner:
    """
    Planner implementation using only deterministic tools — no LLM.

    Delegates to ``build_shape_manifest`` for the full pipeline.
    The component list is extracted from ``garment_spec.components`` order.
    """

    def plan(self, planner_input: PlannerInput) -> PlannerOutput:
        manifest = build_shape_manifest(
            planner_input.garment_spec,
            planner_input.proportion_spec,
            planner_input.measurements,
        )
        component_list = [c.name for c in planner_input.garment_spec.components]
        return PlannerOutput(component_list=component_list, manifest=manifest)
