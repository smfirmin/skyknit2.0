"""Tests for the tolerance calculator."""

import pytest

from utilities.tolerance import PrecisionLevel, calculate_tolerance_mm, gauge_base_mm
from utilities.types import Gauge


@pytest.fixture(scope="module")
def worsted_gauge():
    return Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)


class TestGaugeBaseMm:
    def test_known_value(self, worsted_gauge):
        """5 sts/inch → 25.4 / 5 = 5.08mm per stitch."""
        assert gauge_base_mm(worsted_gauge) == pytest.approx(5.08)

    def test_fine_gauge(self):
        fine = Gauge(stitches_per_inch=8.0, rows_per_inch=10.0)
        assert gauge_base_mm(fine) == pytest.approx(25.4 / 8.0)

    def test_bulky_gauge(self):
        bulky = Gauge(stitches_per_inch=3.0, rows_per_inch=4.0)
        assert gauge_base_mm(bulky) == pytest.approx(25.4 / 3.0)


class TestCalculateToleranceMm:
    def test_known_calculation(self, worsted_gauge):
        """5 sts/inch, ease=1.0, MEDIUM → 5.08 × 1.0 × 1.0 = 5.08mm."""
        result = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.MEDIUM)
        assert result == pytest.approx(5.08)

    def test_high_precision_smaller_than_medium(self, worsted_gauge):
        high = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.HIGH)
        medium = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.MEDIUM)
        assert high < medium

    def test_medium_precision_smaller_than_low(self, worsted_gauge):
        medium = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.MEDIUM)
        low = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.LOW)
        assert medium < low

    def test_precision_ordering(self, worsted_gauge):
        high = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.HIGH)
        medium = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.MEDIUM)
        low = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.LOW)
        assert high < medium < low

    def test_ease_multiplier_scales_linearly(self, worsted_gauge):
        t1 = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.MEDIUM)
        t2 = calculate_tolerance_mm(worsted_gauge, 2.0, PrecisionLevel.MEDIUM)
        assert t2 == pytest.approx(t1 * 2.0)

    def test_ease_at_min_boundary(self, worsted_gauge):
        result = calculate_tolerance_mm(worsted_gauge, 0.75, PrecisionLevel.MEDIUM)
        assert result == pytest.approx(5.08 * 0.75)

    def test_ease_at_max_boundary(self, worsted_gauge):
        result = calculate_tolerance_mm(worsted_gauge, 2.0, PrecisionLevel.MEDIUM)
        assert result == pytest.approx(5.08 * 2.0)

    def test_rejects_ease_below_min(self, worsted_gauge):
        with pytest.raises(ValueError, match="ease_multiplier must be in"):
            calculate_tolerance_mm(worsted_gauge, 0.5, PrecisionLevel.MEDIUM)

    def test_rejects_ease_above_max(self, worsted_gauge):
        with pytest.raises(ValueError, match="ease_multiplier must be in"):
            calculate_tolerance_mm(worsted_gauge, 2.5, PrecisionLevel.MEDIUM)

    def test_high_precision_value(self, worsted_gauge):
        """HIGH = 0.75 → 5.08 × 1.0 × 0.75 = 3.81mm."""
        result = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.HIGH)
        assert result == pytest.approx(5.08 * 0.75)

    def test_low_precision_value(self, worsted_gauge):
        """LOW = 1.5 → 5.08 × 1.0 × 1.5 = 7.62mm."""
        result = calculate_tolerance_mm(worsted_gauge, 1.0, PrecisionLevel.LOW)
        assert result == pytest.approx(5.08 * 1.5)


class TestPrecisionLevelEnum:
    def test_values(self):
        assert PrecisionLevel.HIGH == 0.75
        assert PrecisionLevel.MEDIUM == 1.0
        assert PrecisionLevel.LOW == 1.5

    def test_is_float(self):
        """PrecisionLevel values can be used directly in arithmetic."""
        assert PrecisionLevel.HIGH * 2 == pytest.approx(1.5)
