"""Tests for schemas.constraint — ConstraintObject, StitchMotif, YarnSpec."""

import pytest

from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from utilities.types import Gauge


@pytest.fixture(scope="module")
def worsted_gauge():
    return Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)


@pytest.fixture(scope="module")
def stockinette_motif():
    return StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)


@pytest.fixture(scope="module")
def worsted_yarn():
    return YarnSpec(weight="worsted", fiber="wool", needle_size_mm=5.0)


class TestStitchMotif:
    def test_construction(self):
        m = StitchMotif(name="2x2 rib", stitch_repeat=4, row_repeat=2)
        assert m.name == "2x2 rib"
        assert m.stitch_repeat == 4
        assert m.row_repeat == 2

    def test_is_frozen(self):
        m = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
        with pytest.raises(AttributeError):
            m.stitch_repeat = 2  # type: ignore[misc]

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            StitchMotif(name="", stitch_repeat=1, row_repeat=1)

    def test_rejects_zero_stitch_repeat(self):
        with pytest.raises(ValueError, match="stitch_repeat must be >= 1"):
            StitchMotif(name="x", stitch_repeat=0, row_repeat=1)

    def test_rejects_zero_row_repeat(self):
        with pytest.raises(ValueError, match="row_repeat must be >= 1"):
            StitchMotif(name="x", stitch_repeat=1, row_repeat=0)


class TestYarnSpec:
    def test_construction(self):
        y = YarnSpec(weight="DK", fiber="merino", needle_size_mm=3.75)
        assert y.weight == "DK"
        assert y.fiber == "merino"
        assert y.needle_size_mm == pytest.approx(3.75)

    def test_is_frozen(self):
        y = YarnSpec(weight="worsted", fiber="wool", needle_size_mm=5.0)
        with pytest.raises(AttributeError):
            y.needle_size_mm = 6.0  # type: ignore[misc]

    def test_rejects_zero_needle_size(self):
        with pytest.raises(ValueError, match="needle_size_mm must be positive"):
            YarnSpec(weight="worsted", fiber="wool", needle_size_mm=0.0)

    def test_rejects_negative_needle_size(self):
        with pytest.raises(ValueError, match="needle_size_mm must be positive"):
            YarnSpec(weight="worsted", fiber="wool", needle_size_mm=-1.0)


class TestConstraintObject:
    def test_construction(self, worsted_gauge, stockinette_motif, worsted_yarn):
        co = ConstraintObject(
            gauge=worsted_gauge,
            stitch_motif=stockinette_motif,
            hard_constraints=(4, 2),
            yarn_spec=worsted_yarn,
            physical_tolerance_mm=5.08,
        )
        assert co.gauge is worsted_gauge
        assert co.stitch_motif is stockinette_motif
        assert co.hard_constraints == (4, 2)
        assert co.yarn_spec is worsted_yarn
        assert co.physical_tolerance_mm == pytest.approx(5.08)

    def test_is_frozen(self, worsted_gauge, stockinette_motif, worsted_yarn):
        co = ConstraintObject(
            gauge=worsted_gauge,
            stitch_motif=stockinette_motif,
            hard_constraints=(),
            yarn_spec=worsted_yarn,
            physical_tolerance_mm=5.08,
        )
        with pytest.raises(AttributeError):
            co.physical_tolerance_mm = 10.0  # type: ignore[misc]

    def test_reuses_gauge_from_utilities(self, worsted_gauge, stockinette_motif, worsted_yarn):
        """Gauge type is utilities.types.Gauge — not a redefined schema type."""
        from utilities.types import Gauge as UtilitiesGauge

        co = ConstraintObject(
            gauge=worsted_gauge,
            stitch_motif=stockinette_motif,
            hard_constraints=(),
            yarn_spec=worsted_yarn,
            physical_tolerance_mm=5.08,
        )
        assert isinstance(co.gauge, UtilitiesGauge)

    def test_hard_constraints_as_tuple(self, worsted_gauge, stockinette_motif, worsted_yarn):
        co = ConstraintObject(
            gauge=worsted_gauge,
            stitch_motif=stockinette_motif,
            hard_constraints=(4,),
            yarn_spec=worsted_yarn,
            physical_tolerance_mm=5.08,
        )
        assert isinstance(co.hard_constraints, tuple)

    def test_empty_hard_constraints_allowed(self, worsted_gauge, stockinette_motif, worsted_yarn):
        co = ConstraintObject(
            gauge=worsted_gauge,
            stitch_motif=stockinette_motif,
            hard_constraints=(),
            yarn_spec=worsted_yarn,
            physical_tolerance_mm=5.08,
        )
        assert co.hard_constraints == ()

    def test_rejects_negative_tolerance(self, worsted_gauge, stockinette_motif, worsted_yarn):
        with pytest.raises(ValueError, match="physical_tolerance_mm must be non-negative"):
            ConstraintObject(
                gauge=worsted_gauge,
                stitch_motif=stockinette_motif,
                hard_constraints=(),
                yarn_spec=worsted_yarn,
                physical_tolerance_mm=-1.0,
            )

    def test_rejects_invalid_hard_constraint(self, worsted_gauge, stockinette_motif, worsted_yarn):
        with pytest.raises(ValueError, match="hard_constraints values must be >= 1"):
            ConstraintObject(
                gauge=worsted_gauge,
                stitch_motif=stockinette_motif,
                hard_constraints=(0,),
                yarn_spec=worsted_yarn,
                physical_tolerance_mm=5.08,
            )
