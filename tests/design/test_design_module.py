"""Tests for design.module — EaseLevel, DesignInput, DesignOutput, DeterministicDesignModule."""

from __future__ import annotations

import pytest

from skyknit.design.module import (
    DesignInput,
    DesignModule,
    DesignOutput,
    DeterministicDesignModule,
    EaseLevel,
)
from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec


class TestDesignInput:
    def test_is_frozen(self):
        di = DesignInput(garment_type="top-down-drop-shoulder-pullover")
        with pytest.raises((AttributeError, TypeError)):
            di.ease_level = EaseLevel.FITTED  # type: ignore[misc]

    def test_default_ease_level(self):
        di = DesignInput(garment_type="any")
        assert di.ease_level == EaseLevel.STANDARD

    def test_default_precision(self):
        di = DesignInput(garment_type="any")
        assert di.precision == PrecisionPreference.MEDIUM


class TestDesignModuleProtocol:
    def test_deterministic_module_satisfies_protocol(self):
        assert isinstance(DeterministicDesignModule(), DesignModule)


class TestDeterministicDesignModuleOutput:
    def test_returns_design_output(self):
        out = DeterministicDesignModule().design(DesignInput(garment_type="any"))
        assert isinstance(out, DesignOutput)

    def test_proportion_spec_is_proportion_spec(self):
        out = DeterministicDesignModule().design(DesignInput(garment_type="any"))
        assert isinstance(out.proportion_spec, ProportionSpec)

    def test_precision_propagates_to_proportion_spec(self):
        out = DeterministicDesignModule().design(
            DesignInput(garment_type="any", precision=PrecisionPreference.HIGH)
        )
        assert out.proportion_spec.precision == PrecisionPreference.HIGH

    def test_all_ease_levels_produce_positive_ratios(self):
        module = DeterministicDesignModule()
        for level in EaseLevel:
            out = module.design(DesignInput(garment_type="any", ease_level=level))
            for ratio in out.proportion_spec.ratios.values():
                assert ratio > 0

    def test_fitted_body_ease_less_than_standard(self):
        module = DeterministicDesignModule()
        fitted = module.design(DesignInput("any", ease_level=EaseLevel.FITTED))
        standard = module.design(DesignInput("any", ease_level=EaseLevel.STANDARD))
        assert (
            fitted.proportion_spec.ratios["body_ease"]
            < standard.proportion_spec.ratios["body_ease"]
        )

    def test_standard_body_ease_less_than_relaxed(self):
        module = DeterministicDesignModule()
        standard = module.design(DesignInput("any", ease_level=EaseLevel.STANDARD))
        relaxed = module.design(DesignInput("any", ease_level=EaseLevel.RELAXED))
        assert (
            standard.proportion_spec.ratios["body_ease"]
            < relaxed.proportion_spec.ratios["body_ease"]
        )

    def test_unknown_garment_type_accepted(self):
        """garment_type is accepted but unused in v1; any string value is valid."""
        out = DeterministicDesignModule().design(DesignInput(garment_type="unknown-future-garment"))
        assert out.proportion_spec is not None

    def test_design_output_is_frozen(self):
        out = DeterministicDesignModule().design(DesignInput(garment_type="any"))
        with pytest.raises((AttributeError, TypeError)):
            out.proportion_spec = None  # type: ignore[assignment]
