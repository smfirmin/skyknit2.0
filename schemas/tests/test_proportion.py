"""Tests for schemas.proportion — ProportionSpec and PrecisionPreference."""

import pytest

from schemas.proportion import PrecisionPreference, ProportionSpec


class TestPrecisionPreference:
    def test_values_match_precision_level(self):
        """PrecisionPreference numeric values must match utilities.PrecisionLevel."""
        from utilities.tolerance import PrecisionLevel

        assert PrecisionPreference.HIGH.value == PrecisionLevel.HIGH.value
        assert PrecisionPreference.MEDIUM.value == PrecisionLevel.MEDIUM.value
        assert PrecisionPreference.LOW.value == PrecisionLevel.LOW.value

    def test_is_float_enum(self):
        """PrecisionPreference members behave as floats in arithmetic."""
        assert PrecisionPreference.HIGH * 2 == pytest.approx(1.5)
        assert PrecisionPreference.MEDIUM == pytest.approx(1.0)

    def test_all_members_present(self):
        members = {m.name for m in PrecisionPreference}
        assert members == {"HIGH", "MEDIUM", "LOW"}

    def test_ordering(self):
        """HIGH (tightest) < MEDIUM < LOW (loosest)."""
        assert PrecisionPreference.HIGH < PrecisionPreference.MEDIUM < PrecisionPreference.LOW


class TestProportionSpec:
    def test_construction_with_valid_ratios(self):
        spec = ProportionSpec(
            ratios={"sleeve_length": 0.65, "body_length": 1.0},
            precision=PrecisionPreference.MEDIUM,
        )
        assert spec.ratios["sleeve_length"] == pytest.approx(0.65)
        assert spec.precision is PrecisionPreference.MEDIUM

    def test_is_frozen(self):
        spec = ProportionSpec(
            ratios={"body_length": 1.0},
            precision=PrecisionPreference.HIGH,
        )
        with pytest.raises(AttributeError):
            spec.precision = PrecisionPreference.LOW  # type: ignore[misc]

    def test_ratios_are_dimensionless(self):
        """Ratios are plain floats — no units. Values of 0 are allowed (zero ratio)."""
        spec = ProportionSpec(
            ratios={"yoke_depth": 0.15, "ease": 0.0},
            precision=PrecisionPreference.LOW,
        )
        assert spec.ratios["yoke_depth"] == pytest.approx(0.15)
        assert spec.ratios["ease"] == pytest.approx(0.0)

    def test_rejects_empty_ratios(self):
        with pytest.raises(ValueError, match="ratios must not be empty"):
            ProportionSpec(ratios={}, precision=PrecisionPreference.MEDIUM)

    def test_rejects_negative_ratio_value(self):
        with pytest.raises(ValueError):
            ProportionSpec(
                ratios={"bad": -0.1},
                precision=PrecisionPreference.MEDIUM,
            )

    def test_equality(self):
        s1 = ProportionSpec(ratios={"a": 0.5}, precision=PrecisionPreference.HIGH)
        s2 = ProportionSpec(ratios={"a": 0.5}, precision=PrecisionPreference.HIGH)
        assert s1 == s2

    def test_inequality_different_precision(self):
        s1 = ProportionSpec(ratios={"a": 0.5}, precision=PrecisionPreference.HIGH)
        s2 = ProportionSpec(ratios={"a": 0.5}, precision=PrecisionPreference.LOW)
        assert s1 != s2
