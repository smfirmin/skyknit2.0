"""
DeterministicOrchestrator — wires the full pipeline from GarmentSpec to checked IRs.

Pipeline stages:

  1. DeterministicPlanner.plan()         → ShapeManifest
  2. derive_component_order()            → topological execution order from join graph
  3. validate_phase1()                   → PipelineError("validator") on failure
  4. DeterministicFabricModule.produce() → ConstraintObject per component
  5. DeterministicFiller.fill()          → ComponentIR per component (in derived order)
  6. check_all()                         → retry once on filler-origin failures;
                                           PipelineError("checker") if still failing

Retry logic (v1): if check_all returns filler-origin errors, affected components
are re-filled with their physical_tolerance_mm widened by ×1.5 and check_all is
re-run once.  Geometric-origin errors are not retried (those require Planner
intervention).

A future OrchestratorInput can carry LLM planner / fabric module / filler
variants — the protocol boundary is the input/output dataclasses, not the
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from skyknit.checker.checker import CheckerResult, check_all
from skyknit.fabric.module import DeterministicFabricModule, FabricInput
from skyknit.fillers.filler import DeterministicFiller, FillerInput
from skyknit.planner.ordering import derive_component_order
from skyknit.planner.planner import DeterministicPlanner, PlannerInput
from skyknit.schemas.constraint import ConstraintObject
from skyknit.schemas.garment import GarmentSpec
from skyknit.schemas.ir import ComponentIR
from skyknit.schemas.manifest import ShapeManifest
from skyknit.schemas.proportion import ProportionSpec
from skyknit.validator.phase1 import validate_phase1


class PipelineError(Exception):
    """Raised when a pipeline stage fails.

    Attributes:
        stage: Name of the stage that failed
            (``"planner"``, ``"validator"``, ``"filler"``, or ``"checker"``).
        detail: Human-readable description of the failure.
    """

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"[{stage}] {detail}")
        self.stage = stage
        self.detail = detail


@dataclass(frozen=True)
class OrchestratorInput:
    """Complete input bundle for the DeterministicOrchestrator."""

    garment_spec: GarmentSpec
    proportion_spec: ProportionSpec
    measurements: dict[str, float]  # all in mm
    fabric_input: FabricInput


@dataclass(frozen=True)
class OrchestratorOutput:
    """Output of a successful pipeline run."""

    manifest: ShapeManifest
    component_order: list[str]  # topological construction order (from join graph)
    irs: dict[str, ComponentIR]
    constraints: dict[str, ConstraintObject]
    checker_result: CheckerResult


class DeterministicOrchestrator:
    """
    Fully deterministic pipeline orchestrator.

    Runs all stages in sequence.  Any failure raises :class:`PipelineError`
    with the failing stage name.  No retry logic — callers should inspect the
    error and decide whether to adjust inputs and re-run.
    """

    def run(self, oi: OrchestratorInput) -> OrchestratorOutput:
        """Execute the full pipeline and return a completed :class:`OrchestratorOutput`.

        Parameters
        ----------
        oi:
            Input bundle containing garment spec, proportion spec, measurements,
            and fabric parameters.

        Returns
        -------
        OrchestratorOutput
            Manifest, topological component order, all ComponentIRs, all
            ConstraintObjects, and the Algebraic Checker result.

        Raises
        ------
        PipelineError
            If any pipeline stage fails.  The ``stage`` attribute names the
            failing module.
        """
        # Stage 1: Planner → ShapeManifest
        try:
            planner_out = DeterministicPlanner().plan(
                PlannerInput(
                    garment_spec=oi.garment_spec,
                    proportion_spec=oi.proportion_spec,
                    measurements=oi.measurements,
                )
            )
        except Exception as exc:
            raise PipelineError("planner", str(exc)) from exc

        manifest: ShapeManifest = planner_out.manifest

        # Stage 2: Derive construction order from join graph
        component_order = derive_component_order(manifest)

        # Stage 3: Geometric Validator Phase 1
        validation = validate_phase1(manifest)
        if not validation.passed:
            error_msgs = "; ".join(str(e) for e in validation.errors)
            raise PipelineError("validator", error_msgs)

        # Stage 4: Fabric Module → ConstraintObject per component
        fabric_out = DeterministicFabricModule().produce(
            FabricInput(
                component_names=tuple(component_order),
                gauge=oi.fabric_input.gauge,
                stitch_motif=oi.fabric_input.stitch_motif,
                yarn_spec=oi.fabric_input.yarn_spec,
                precision=oi.fabric_input.precision,
            )
        )
        constraints: dict[str, ConstraintObject] = fabric_out.constraints

        # Stage 5: Stitch Fillers — one DeterministicFiller per component, in order
        filler = DeterministicFiller()
        irs: dict[str, ComponentIR] = {}

        for comp_name in component_order:
            comp_spec = next(c for c in manifest.components if c.name == comp_name)
            comp_joins = tuple(
                j
                for j in manifest.joins
                if comp_name in (j.edge_a_ref.split(".")[0], j.edge_b_ref.split(".")[0])
            )
            try:
                fill_out = filler.fill(
                    FillerInput(
                        component_spec=comp_spec,
                        constraint=constraints[comp_name],
                        joins=comp_joins,
                        handedness=comp_spec.handedness,
                    )
                )
            except Exception as exc:
                raise PipelineError("filler", f"component '{comp_name}': {exc}") from exc

            irs[comp_name] = fill_out.ir

        # Stage 6: Algebraic Checker — with single retry for filler-origin failures
        checker_result = check_all(manifest=manifest, irs=irs, constraints=constraints)
        if not checker_result.passed:
            filler_components = {
                e.component_name for e in checker_result.errors if e.error_type == "filler_origin"
            }
            if filler_components:
                # Retry: widen tolerance ×1.5 for affected components and re-fill.
                irs, constraints = _retry_filler_components(
                    manifest, irs, constraints, filler_components
                )
                checker_result = check_all(manifest=manifest, irs=irs, constraints=constraints)

            if not checker_result.passed:
                error_msgs = "; ".join(str(e) for e in checker_result.errors)
                raise PipelineError("checker", error_msgs)

        return OrchestratorOutput(
            manifest=manifest,
            component_order=component_order,
            irs=irs,
            constraints=constraints,
            checker_result=checker_result,
        )


# ── Retry helper ──────────────────────────────────────────────────────────────


def _retry_filler_components(
    manifest: ShapeManifest,
    irs: dict[str, ComponentIR],
    constraints: dict[str, ConstraintObject],
    failed_components: set[str],
) -> tuple[dict[str, ComponentIR], dict[str, ConstraintObject]]:
    """
    Re-fill *failed_components* with physical_tolerance_mm widened by ×1.5.

    Returns updated copies of *irs* and *constraints* dicts.  Components not
    in *failed_components* are left unchanged.
    """
    new_irs = dict(irs)
    new_constraints = dict(constraints)
    filler = DeterministicFiller()

    for comp_name in failed_components:
        comp_spec = next(c for c in manifest.components if c.name == comp_name)
        old = constraints[comp_name]
        widened = ConstraintObject(
            gauge=old.gauge,
            stitch_motif=old.stitch_motif,
            hard_constraints=old.hard_constraints,
            yarn_spec=old.yarn_spec,
            physical_tolerance_mm=old.physical_tolerance_mm * 1.5,
        )
        comp_joins = tuple(
            j
            for j in manifest.joins
            if comp_name in (j.edge_a_ref.split(".")[0], j.edge_b_ref.split(".")[0])
        )
        try:
            fill_out = filler.fill(
                FillerInput(
                    component_spec=comp_spec,
                    constraint=widened,
                    joins=comp_joins,
                    handedness=comp_spec.handedness,
                )
            )
        except Exception as exc:
            raise PipelineError("filler", f"component '{comp_name}' (retry): {exc}") from exc

        new_irs[comp_name] = fill_out.ir
        new_constraints[comp_name] = widened

    return new_irs, new_constraints
