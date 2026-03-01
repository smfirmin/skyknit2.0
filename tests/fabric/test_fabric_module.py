"""Tests for fabric.module — FabricInput, FabricOutput, DeterministicFabricModule."""

from __future__ import annotations

import pytest

from skyknit.fabric.module import DeterministicFabricModule, FabricInput, FabricModule, FabricOutput
from skyknit.schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.utilities.types import Gauge

# ── Shared helpers ─────────────────────────────────────────────────────────────


def _gauge() -> Gauge:
    return Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)


def _motif() -> StitchMotif:
    return StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)


def _yarn() -> YarnSpec:
    return YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0)


def _input(
    component_names: tuple[str, ...] = ("body", "left_sleeve", "right_sleeve"),
    precision: PrecisionPreference = PrecisionPreference.MEDIUM,
) -> FabricInput:
    return FabricInput(
        component_names=component_names,
        gauge=_gauge(),
        stitch_motif=_motif(),
        yarn_spec=_yarn(),
        precision=precision,
    )


# ── FabricInput ────────────────────────────────────────────────────────────────


class TestFabricInput:
    def test_is_frozen(self):
        fi = _input()
        with pytest.raises((AttributeError, TypeError)):
            fi.gauge = _gauge()  # type: ignore[misc]

    def test_stores_fields(self):
        fi = _input(component_names=("body",))
        assert fi.component_names == ("body",)
        assert fi.precision == PrecisionPreference.MEDIUM


# ── FabricOutput ───────────────────────────────────────────────────────────────


class TestFabricOutput:
    def test_is_frozen(self):
        out = FabricOutput(constraints={})
        with pytest.raises((AttributeError, TypeError)):
            out.constraints = {}  # type: ignore[misc]


# ── DeterministicFabricModule ──────────────────────────────────────────────────


class TestDeterministicFabricModule:
    def test_satisfies_protocol(self):
        assert isinstance(DeterministicFabricModule(), FabricModule)

    def test_constraint_keys_match_component_names(self):
        names = ("body", "left_sleeve", "right_sleeve")
        output = DeterministicFabricModule().produce(_input(component_names=names))
        assert set(output.constraints.keys()) == set(names)

    def test_each_constraint_is_constraint_object(self):
        output = DeterministicFabricModule().produce(_input())
        for constraint in output.constraints.values():
            assert isinstance(constraint, ConstraintObject)

    def test_gauge_propagated(self):
        gauge = Gauge(stitches_per_inch=24.0, rows_per_inch=32.0)
        fi = FabricInput(
            component_names=("body",),
            gauge=gauge,
            stitch_motif=_motif(),
            yarn_spec=_yarn(),
            precision=PrecisionPreference.MEDIUM,
        )
        output = DeterministicFabricModule().produce(fi)
        assert output.constraints["body"].gauge == gauge

    def test_tolerance_is_positive(self):
        output = DeterministicFabricModule().produce(_input())
        for constraint in output.constraints.values():
            assert constraint.physical_tolerance_mm > 0.0

    def test_high_precision_tighter_than_low(self):
        """HIGH precision → smaller tolerance band than LOW, for the same gauge."""
        out_high = DeterministicFabricModule().produce(_input(precision=PrecisionPreference.HIGH))
        out_low = DeterministicFabricModule().produce(_input(precision=PrecisionPreference.LOW))
        tol_high = out_high.constraints["body"].physical_tolerance_mm
        tol_low = out_low.constraints["body"].physical_tolerance_mm
        assert tol_high < tol_low

    def test_empty_component_names_returns_empty_constraints(self):
        output = DeterministicFabricModule().produce(_input(component_names=()))
        assert output.constraints == {}

    def test_stitch_motif_propagated(self):
        motif = StitchMotif(name="2x2 ribbing", stitch_repeat=4, row_repeat=2)
        fi = FabricInput(
            component_names=("body",),
            gauge=_gauge(),
            stitch_motif=motif,
            yarn_spec=_yarn(),
            precision=PrecisionPreference.MEDIUM,
        )
        output = DeterministicFabricModule().produce(fi)
        assert output.constraints["body"].stitch_motif == motif
