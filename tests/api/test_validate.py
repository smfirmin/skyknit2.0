"""
Tests for skyknit/api/validate.py — ValidationReport and validate_pattern().

All tests use a deterministic mock parser (no LLM calls), so they are
fully CI-safe.  The mock is injected via the ``parser`` parameter of
``validate_pattern()``.
"""

from __future__ import annotations

import pytest

from skyknit.api.validate import ValidationReport, validate_pattern
from skyknit.parser.parser import (
    ParsedComponent,
    ParsedOperation,
    ParsedPattern,
    ParseError,
    ParserInput,
    ParserOutput,
    _assemble,
)
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.utilities.types import Gauge

# ── Shared fixtures ────────────────────────────────────────────────────────────

_GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
_MOTIF = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
_YARN = YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0)
_PRECISION = PrecisionPreference.MEDIUM


def _make_passing_parsed() -> ParsedPattern:
    """Minimal self-consistent ParsedPattern that passes check_all()."""
    body = ParsedComponent(
        name="body",
        handedness="NONE",
        starting_stitch_count=80,
        ending_stitch_count=0,
        operations=(
            ParsedOperation("CAST_ON", 80, None, {"count": 80}),
            ParsedOperation("WORK_EVEN", 80, 100, {}),
            ParsedOperation("BIND_OFF", 0, None, {"count": 80}),
        ),
    )
    return ParsedPattern(
        components=(body,),
        joins=(),
        gauge=None,
        garment_type_hint=None,
    )


def _make_failing_parsed() -> ParsedPattern:
    """ParsedPattern with an inconsistent stitch count — check_all() fails."""
    body = ParsedComponent(
        name="body",
        handedness="NONE",
        starting_stitch_count=80,
        ending_stitch_count=999,  # wrong: BIND_OFF sets live to 0, not 999
        operations=(
            ParsedOperation("CAST_ON", 80, None, {"count": 80}),
            ParsedOperation("BIND_OFF", 0, None, {"count": 80}),
        ),
    )
    return ParsedPattern(
        components=(body,),
        joins=(),
        gauge=None,
        garment_type_hint=None,
    )


class _PassingMockParser:
    """Mock parser that always returns a passing ParsedPattern."""

    def parse(self, pi: ParserInput) -> ParserOutput:
        parsed = _make_passing_parsed()
        return _assemble(parsed, pi)


class _FailingMockParser:
    """Mock parser that returns a ParsedPattern with bad stitch counts."""

    def parse(self, pi: ParserInput) -> ParserOutput:
        parsed = _make_failing_parsed()
        return _assemble(parsed, pi)


class _ErrorMockParser:
    """Mock parser that always raises ParseError."""

    def parse(self, pi: ParserInput) -> ParserOutput:
        raise ParseError("mock parse failure")


class _RuntimeErrorParser:
    """Mock parser that raises a generic RuntimeError (not ParseError)."""

    def parse(self, pi: ParserInput) -> ParserOutput:
        raise RuntimeError("unexpected error")


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestValidationReport:
    def test_report_is_frozen_dataclass(self):
        report = ValidationReport(
            passed=True, checker_result=None, parsed_pattern=None, parse_error=None
        )
        with pytest.raises((AttributeError, TypeError)):
            report.passed = False  # type: ignore[misc]

    def test_fields_accessible(self):
        report = ValidationReport(
            passed=True, checker_result=None, parsed_pattern=None, parse_error=None
        )
        assert report.passed is True
        assert report.checker_result is None
        assert report.parsed_pattern is None
        assert report.parse_error is None


class TestValidatePatternWithMockParser:
    def test_returns_validation_report_type(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_PassingMockParser())
        assert isinstance(report, ValidationReport)

    def test_mock_parser_passes(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_PassingMockParser())
        assert report.passed is True

    def test_mock_parser_wrong_count_fails(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_FailingMockParser())
        assert report.passed is False

    def test_parse_error_captured_in_report(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_ErrorMockParser())
        assert report.passed is False
        assert report.parse_error is not None
        assert "mock parse failure" in report.parse_error

    def test_checker_result_none_on_parse_error(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_ErrorMockParser())
        assert report.checker_result is None

    def test_parsed_pattern_none_on_parse_error(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_ErrorMockParser())
        assert report.parsed_pattern is None

    def test_checker_result_populated_on_pass(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_PassingMockParser())
        assert report.checker_result is not None
        assert report.checker_result.passed is True

    def test_parsed_pattern_populated_on_pass(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_PassingMockParser())
        assert report.parsed_pattern is not None

    def test_runtime_error_also_captured(self):
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_RuntimeErrorParser())
        assert report.passed is False
        assert report.parse_error is not None

    def test_precision_default_is_medium(self):
        # Just confirm the call succeeds without explicit precision kwarg
        report = validate_pattern("text", _GAUGE, _MOTIF, _YARN, parser=_PassingMockParser())
        assert isinstance(report, ValidationReport)
