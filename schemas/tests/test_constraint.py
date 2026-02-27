"""Tests for schemas.constraint — ConstraintObject, StitchMotif, YarnSpec."""

import pytest

from schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from utilities import Gauge


@pytest.fixture
def sample_gauge():
    return Gauge(stitches_per_inch=5.0, rows_per_inch=7.0)


@pytest.fixture
def sample_motif():
    return StitchMotif(name="2x2 ribbing", stitch_repeat=4, row_repeat=1)


@pytest.fixture
def sample_yarn():
    return YarnSpec(weight="DK", fiber="100% merino wool", needle_size_mm=3.75)


@pytest.fixture
def sample_constraint(sample_gauge, sample_motif, sample_yarn):
    return ConstraintObject(
        gauge=sample_gauge,
        stitch_motif=sample_motif,
        hard_constraints=(4, 6),
        yarn_spec=sample_yarn,
        physical_tolerance_mm=5.08,
    )


class TestStitchMotif:
    def test_construction(self):
        motif = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
        assert motif.name == "stockinette"
        assert motif.stitch_repeat == 1
        assert motif.row_repeat == 1

    def test_is_frozen(self, sample_motif):
        with pytest.raises(Exception):
            sample_motif.stitch_repeat = 8


class TestYarnSpec:
    def test_construction(self, sample_yarn):
        assert sample_yarn.weight == "DK"
        assert sample_yarn.fiber == "100% merino wool"
        assert sample_yarn.needle_size_mm == 3.75

    def test_is_frozen(self, sample_yarn):
        with pytest.raises(Exception):
            sample_yarn.weight = "worsted"


class TestConstraintObject:
    def test_all_fields_accessible(
        self, sample_constraint, sample_gauge, sample_motif, sample_yarn
    ):
        assert sample_constraint.gauge == sample_gauge
        assert sample_constraint.stitch_motif == sample_motif
        assert sample_constraint.hard_constraints == (4, 6)
        assert sample_constraint.yarn_spec == sample_yarn
        assert sample_constraint.physical_tolerance_mm == 5.08

    def test_is_frozen(self, sample_constraint):
        with pytest.raises(Exception):
            sample_constraint.physical_tolerance_mm = 10.0

    def test_reuses_gauge_from_utilities(self, sample_constraint):
        """Gauge must be utilities.Gauge — not a duplicate schema-local type."""
        from utilities.types import Gauge as UtilGauge

        assert isinstance(sample_constraint.gauge, UtilGauge)

    def test_hard_constraints_is_tuple(self, sample_constraint):
        assert isinstance(sample_constraint.hard_constraints, tuple)

    def test_empty_hard_constraints(self, sample_gauge, sample_motif, sample_yarn):
        obj = ConstraintObject(
            gauge=sample_gauge,
            stitch_motif=sample_motif,
            hard_constraints=(),
            yarn_spec=sample_yarn,
            physical_tolerance_mm=3.0,
        )
        assert obj.hard_constraints == ()
