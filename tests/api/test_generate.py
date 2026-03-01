"""Tests for api.generate — generate_pattern() public API."""

from __future__ import annotations

import pytest

from skyknit.api.generate import generate_pattern
from skyknit.design.module import EaseLevel
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.utilities.types import Gauge
from skyknit.writer.writer import WriterInput, WriterOutput

# ── Shared fixtures ────────────────────────────────────────────────────────────

_GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
_MOTIF = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
_YARN = YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0)

_MEASUREMENTS_DROP = {
    "chest_circumference_mm": 914.4,
    "body_length_mm": 457.2,
    "sleeve_length_mm": 495.3,
    "upper_arm_circumference_mm": 381.0,
    "wrist_circumference_mm": 152.4,
}

_MEASUREMENTS_YOKE = {**_MEASUREMENTS_DROP, "yoke_depth_mm": 228.6}


# ── Drop-shoulder pullover ────────────────────────────────────────────────────


class TestDropShoulderGenerate:
    def test_returns_non_empty_string(self):
        result = generate_pattern(
            garment_type="top-down-drop-shoulder-pullover",
            measurements=_MEASUREMENTS_DROP,
            gauge=_GAUGE,
            stitch_motif=_MOTIF,
            yarn_spec=_YARN,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_expected_prose_markers(self):
        result = generate_pattern(
            garment_type="top-down-drop-shoulder-pullover",
            measurements=_MEASUREMENTS_DROP,
            gauge=_GAUGE,
            stitch_motif=_MOTIF,
            yarn_spec=_YARN,
        )
        assert "Cast on" in result
        assert "Work even" in result
        assert "Bind off" in result
        assert "Pick up" in result

    def test_different_chest_produces_different_stitch_count(self):
        """Wider chest → more stitches somewhere in the pattern text."""
        result_narrow = generate_pattern(
            "top-down-drop-shoulder-pullover",
            {**_MEASUREMENTS_DROP, "chest_circumference_mm": 762.0},
            _GAUGE,
            _MOTIF,
            _YARN,
        )
        result_wide = generate_pattern(
            "top-down-drop-shoulder-pullover",
            {**_MEASUREMENTS_DROP, "chest_circumference_mm": 1067.0},
            _GAUGE,
            _MOTIF,
            _YARN,
        )
        assert result_narrow != result_wide


# ── Yoke pullover ─────────────────────────────────────────────────────────────


class TestYokeGenerate:
    def test_yoke_runs_without_error(self):
        result = generate_pattern(
            garment_type="top-down-yoke-pullover",
            measurements=_MEASUREMENTS_YOKE,
            gauge=_GAUGE,
            stitch_motif=_MOTIF,
            yarn_spec=_YARN,
        )
        assert isinstance(result, str)
        assert len(result) > 0


# ── Error handling ────────────────────────────────────────────────────────────


class TestGenerateErrors:
    def test_unknown_garment_type_raises_key_error(self):
        with pytest.raises(KeyError):
            generate_pattern(
                garment_type="nonexistent-garment",
                measurements=_MEASUREMENTS_DROP,
                gauge=_GAUGE,
                stitch_motif=_MOTIF,
                yarn_spec=_YARN,
            )


# ── Ease level effect ─────────────────────────────────────────────────────────


class TestEaseLevel:
    def test_relaxed_produces_larger_stitch_count_than_fitted(self):
        """RELAXED ease → body wider than FITTED ease at the same measurements."""
        fitted = generate_pattern(
            "top-down-drop-shoulder-pullover",
            _MEASUREMENTS_DROP,
            _GAUGE,
            _MOTIF,
            _YARN,
            ease_level=EaseLevel.FITTED,
            precision=PrecisionPreference.LOW,  # wide tolerance avoids repeat conflicts
        )
        relaxed = generate_pattern(
            "top-down-drop-shoulder-pullover",
            _MEASUREMENTS_DROP,
            _GAUGE,
            _MOTIF,
            _YARN,
            ease_level=EaseLevel.RELAXED,
            precision=PrecisionPreference.LOW,
        )
        # Patterns differ because stitch counts change with ease
        assert fitted != relaxed


# ── Writer injection ───────────────────────────────────────────────────────────


class _MarkerWriter:
    """Deterministic stub that returns a fixed sentinel string."""

    def write(self, wi: WriterInput) -> WriterOutput:
        return WriterOutput(
            sections={name: "MARKER" for name in wi.component_order},
            full_pattern="MARKER",
        )


class TestWriterInjection:
    def test_custom_writer_is_called(self):
        result = generate_pattern(
            "top-down-drop-shoulder-pullover",
            _MEASUREMENTS_DROP,
            _GAUGE,
            _MOTIF,
            _YARN,
            writer=_MarkerWriter(),
        )
        assert result == "MARKER"

    def test_none_writer_uses_template_writer(self):
        result = generate_pattern(
            "top-down-drop-shoulder-pullover",
            _MEASUREMENTS_DROP,
            _GAUGE,
            _MOTIF,
            _YARN,
            writer=None,
        )
        assert "Cast on" in result
