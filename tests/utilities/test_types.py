"""Tests for utilities type definitions."""

import pytest

from skyknit.utilities.types import Gauge


class TestGauge:
    def test_construction_with_valid_values(self):
        g = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        assert g.stitches_per_inch == 5.0
        assert g.rows_per_inch == 7.0

    def test_is_frozen(self):
        g = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        with pytest.raises(AttributeError):
            g.stitches_per_inch = 6.0  # type: ignore[misc]

    def test_rejects_zero_stitches_per_inch(self):
        with pytest.raises(ValueError, match="stitches_per_inch must be positive"):
            Gauge(stitches_per_inch=0, rows_per_inch=7.0)

    def test_rejects_negative_stitches_per_inch(self):
        with pytest.raises(ValueError, match="stitches_per_inch must be positive"):
            Gauge(stitches_per_inch=-1.0, rows_per_inch=7.0)

    def test_rejects_zero_rows_per_inch(self):
        with pytest.raises(ValueError, match="rows_per_inch must be positive"):
            Gauge(stitches_per_inch=5.0, rows_per_inch=0)

    def test_rejects_negative_rows_per_inch(self):
        with pytest.raises(ValueError, match="rows_per_inch must be positive"):
            Gauge(stitches_per_inch=5.0, rows_per_inch=-3.0)

    def test_equality(self):
        g1 = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        g2 = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        assert g1 == g2

    def test_inequality(self):
        g1 = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        g2 = Gauge(stitches_per_inch=6.0, rows_per_inch=7.0)
        assert g1 != g2

    def test_hashable(self):
        g = Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)
        assert hash(g) is not None
        # Can be used as dict key
        d = {g: "worsted"}
        assert d[g] == "worsted"
