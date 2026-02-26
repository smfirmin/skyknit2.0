"""Tests for unit conversion functions."""

import pytest

from utilities.conversion import (
    MM_PER_INCH,
    inches_to_mm,
    mm_to_inches,
    physical_to_row_count,
    physical_to_section_rows,
    physical_to_stitch_count,
    row_count_to_physical,
    stitch_count_to_physical,
)
from utilities.types import Gauge


@pytest.fixture(scope="module")
def worsted_gauge():
    """Typical worsted-weight gauge: 5 sts/inch, 7 rows/inch."""
    return Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)


class TestInchesMillimeters:
    def test_inches_to_mm_one_inch(self):
        assert inches_to_mm(1.0) == 25.4

    def test_mm_to_inches_one_inch(self):
        assert mm_to_inches(25.4) == 1.0

    def test_round_trip_inches(self):
        for val in [0.5, 1.0, 3.75, 10.0, 36.0]:
            assert mm_to_inches(inches_to_mm(val)) == pytest.approx(val)

    def test_round_trip_mm(self):
        for val in [12.7, 25.4, 100.0, 254.0, 914.4]:
            assert inches_to_mm(mm_to_inches(val)) == pytest.approx(val)

    def test_zero(self):
        assert inches_to_mm(0.0) == 0.0
        assert mm_to_inches(0.0) == 0.0

    def test_mm_per_inch_constant(self):
        assert MM_PER_INCH == 25.4


class TestPhysicalToStitchCount:
    def test_known_value(self, worsted_gauge):
        """1 inch (25.4mm) at 5 sts/inch = 5.0 stitches."""
        assert physical_to_stitch_count(25.4, worsted_gauge) == pytest.approx(5.0)

    def test_ten_inches(self, worsted_gauge):
        """10 inches (254mm) at 5 sts/inch = 50.0 stitches."""
        assert physical_to_stitch_count(254.0, worsted_gauge) == pytest.approx(50.0)

    def test_zero_dimension(self, worsted_gauge):
        assert physical_to_stitch_count(0.0, worsted_gauge) == 0.0

    def test_round_trip(self, worsted_gauge):
        for dim in [25.4, 127.0, 254.0, 508.0]:
            raw = physical_to_stitch_count(dim, worsted_gauge)
            back = stitch_count_to_physical(raw, worsted_gauge)
            assert back == pytest.approx(dim)


class TestPhysicalToRowCount:
    def test_known_value(self, worsted_gauge):
        """1 inch (25.4mm) at 7 rows/inch = 7.0 rows."""
        assert physical_to_row_count(25.4, worsted_gauge) == pytest.approx(7.0)

    def test_zero_dimension(self, worsted_gauge):
        assert physical_to_row_count(0.0, worsted_gauge) == 0.0

    def test_round_trip(self, worsted_gauge):
        for dim in [25.4, 127.0, 254.0]:
            raw = physical_to_row_count(dim, worsted_gauge)
            back = row_count_to_physical(raw, worsted_gauge)
            assert back == pytest.approx(dim)


class TestStitchCountToPhysical:
    def test_known_value(self, worsted_gauge):
        """5 stitches at 5 sts/inch = 1 inch = 25.4mm."""
        assert stitch_count_to_physical(5.0, worsted_gauge) == pytest.approx(25.4)

    def test_zero_count(self, worsted_gauge):
        assert stitch_count_to_physical(0.0, worsted_gauge) == 0.0


class TestRowCountToPhysical:
    def test_known_value(self, worsted_gauge):
        """7 rows at 7 rows/inch = 1 inch = 25.4mm."""
        assert row_count_to_physical(7.0, worsted_gauge) == pytest.approx(25.4)

    def test_zero_count(self, worsted_gauge):
        assert row_count_to_physical(0.0, worsted_gauge) == 0.0


class TestDifferentGauges:
    def test_fine_gauge(self):
        """Fine gauge: 8 sts/inch. 1 inch = 8 stitches."""
        fine = Gauge(stitches_per_inch=8.0, rows_per_inch=10.0)
        assert physical_to_stitch_count(25.4, fine) == pytest.approx(8.0)
        assert physical_to_row_count(25.4, fine) == pytest.approx(10.0)

    def test_bulky_gauge(self):
        """Bulky gauge: 3 sts/inch. 1 inch = 3 stitches."""
        bulky = Gauge(stitches_per_inch=3.0, rows_per_inch=4.0)
        assert physical_to_stitch_count(25.4, bulky) == pytest.approx(3.0)
        assert physical_to_row_count(25.4, bulky) == pytest.approx(4.0)


class TestNegativeDimensions:
    """Conversion functions are pure math — negative inputs produce negative outputs."""

    def test_negative_stitch_count(self, worsted_gauge):
        assert physical_to_stitch_count(-25.4, worsted_gauge) == pytest.approx(-5.0)

    def test_negative_row_count(self, worsted_gauge):
        assert physical_to_row_count(-25.4, worsted_gauge) == pytest.approx(-7.0)

    def test_negative_round_trip(self, worsted_gauge):
        raw = physical_to_stitch_count(-127.0, worsted_gauge)
        back = stitch_count_to_physical(raw, worsted_gauge)
        assert back == pytest.approx(-127.0)


class TestPhysicalToSectionRows:
    def test_exact_integer(self, worsted_gauge):
        """25.4mm (1") at 7 rows/inch → exactly 7 rows."""
        assert physical_to_section_rows(25.4, worsted_gauge) == 7

    def test_rounds_to_nearest(self, worsted_gauge):
        """254mm (10") at 7 rows/inch → 70.0 rows exactly."""
        assert physical_to_section_rows(254.0, worsted_gauge) == 70

    def test_rounds_up_from_half(self):
        """Banker's rounding: 0.5 rounds to nearest even (Python round behaviour)."""
        # 3 rows/inch, 2 inches = 6.0 (exact). Slightly more → 6 or 7 depending on rounding.
        gauge = Gauge(stitches_per_inch=5.0, rows_per_inch=3.0)
        # 55mm → 55/25.4 * 3 ≈ 6.496 → rounds to 6
        assert physical_to_section_rows(55.0, gauge) == 6
        # 57mm → 57/25.4 * 3 ≈ 6.732 → rounds to 7
        assert physical_to_section_rows(57.0, gauge) == 7

    def test_returns_int(self, worsted_gauge):
        result = physical_to_section_rows(100.0, worsted_gauge)
        assert isinstance(result, int)

    def test_zero(self, worsted_gauge):
        assert physical_to_section_rows(0.0, worsted_gauge) == 0
