"""Tests for schemas.proportion — ProportionSpec and PrecisionPreference."""

from types import MappingProxyType

import pytest

from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec
from skyknit.utilities import PrecisionLevel


class TestPrecisionPreference:
    def test_members_exist(self):
        assert PrecisionPreference.HIGH
        assert PrecisionPreference.MEDIUM
        assert PrecisionPreference.LOW

    def test_maps_to_precision_level_values(self):
        """PrecisionPreference names must align with utilities.PrecisionLevel names."""
        for pref in PrecisionPreference:
            assert pref.name in PrecisionLevel.__members__, (
                f"PrecisionPreference.{pref.name} has no matching PrecisionLevel"
            )

    def test_is_string_enum(self):
        assert isinstance(PrecisionPreference.HIGH, str)

    def test_to_precision_level_returns_correct_level(self):
        assert PrecisionPreference.HIGH.to_precision_level() is PrecisionLevel.HIGH
        assert PrecisionPreference.MEDIUM.to_precision_level() is PrecisionLevel.MEDIUM
        assert PrecisionPreference.LOW.to_precision_level() is PrecisionLevel.LOW

    def test_to_precision_level_values_match(self):
        """Numeric values carried by PrecisionLevel must match documented mapping."""
        assert PrecisionPreference.HIGH.to_precision_level().value == 0.75
        assert PrecisionPreference.MEDIUM.to_precision_level().value == 1.0
        assert PrecisionPreference.LOW.to_precision_level().value == 1.5

    def test_to_precision_level_covers_all_members(self):
        """Every PrecisionPreference member must map to a PrecisionLevel without error."""
        for pref in PrecisionPreference:
            level = pref.to_precision_level()
            assert isinstance(level, PrecisionLevel)


class TestProportionSpec:
    def test_construction(self):
        spec = ProportionSpec(
            ratios=MappingProxyType({"body_length": 0.6, "sleeve_length": 0.55}),
            precision=PrecisionPreference.MEDIUM,
        )
        assert spec.ratios["body_length"] == 0.6
        assert spec.precision == PrecisionPreference.MEDIUM

    def test_is_frozen(self):
        spec = ProportionSpec(
            ratios=MappingProxyType({"a": 1.0}),
            precision=PrecisionPreference.HIGH,
        )
        with pytest.raises(Exception):
            spec.precision = PrecisionPreference.LOW  # type: ignore[misc]

    def test_ratios_are_dimensionless(self):
        """Ratios should be plain floats — no unit attached."""
        spec = ProportionSpec(
            ratios=MappingProxyType({"yoke_depth": 0.25}),
            precision=PrecisionPreference.LOW,
        )
        assert isinstance(spec.ratios["yoke_depth"], float)

    def test_requires_mapping_proxy(self):
        with pytest.raises(TypeError):
            ProportionSpec(
                ratios={"body_length": 0.6},  # type: ignore[arg-type]
                precision=PrecisionPreference.MEDIUM,
            )

    def test_ratios_immutable(self):
        spec = ProportionSpec(
            ratios=MappingProxyType({"x": 1.0}),
            precision=PrecisionPreference.MEDIUM,
        )
        with pytest.raises(TypeError):
            spec.ratios["x"] = 2.0  # type: ignore[index]
