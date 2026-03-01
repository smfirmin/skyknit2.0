"""
Public pattern validation API.

validate_pattern() parses a free-text knitting pattern using a PatternParser
and validates the resulting IR with the Algebraic Checker.  It returns a
ValidationReport regardless of whether parsing or checking succeeds, so callers
can inspect partial results on failure.

The default parser is LLMPatternParser (requires the anthropic package).
For testing and CI, inject any object satisfying the PatternParser Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass

from skyknit.checker.checker import CheckerResult, check_all
from skyknit.parser.parser import (
    ParsedPattern,
    ParserInput,
    PatternParser,
)
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.utilities.types import Gauge


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of validating a knitting pattern.

    Attributes:
        passed: True only when both parsing and algebraic checking succeeded.
        checker_result: The CheckerResult from check_all(), or None if parsing failed.
        parsed_pattern: The intermediate ParsedPattern from the LLM, or None if parsing failed.
        parse_error: Error message string if parsing raised, else None.
    """

    passed: bool
    checker_result: CheckerResult | None
    parsed_pattern: ParsedPattern | None
    parse_error: str | None


def validate_pattern(
    pattern_text: str,
    gauge: Gauge,
    stitch_motif: StitchMotif,
    yarn_spec: YarnSpec,
    parser: PatternParser | None = None,
    precision: PrecisionPreference = PrecisionPreference.MEDIUM,
) -> ValidationReport:
    """
    Parse and validate a knitting pattern text.

    Parameters
    ----------
    pattern_text:
        Raw knitting pattern prose to validate.
    gauge:
        Knitting gauge (stitches per inch and rows per inch).
    stitch_motif:
        Stitch pattern for constraint construction.
    yarn_spec:
        Yarn weight, fibre, and needle size.
    parser:
        A PatternParser implementation.  If None, an LLMPatternParser is
        created (requires the anthropic package and ANTHROPIC_API_KEY env var).
    precision:
        Tolerance precision preference; defaults to MEDIUM.

    Returns
    -------
    ValidationReport
        Always returned — never raises.  Inspect ``passed``, ``checker_result``,
        and ``parse_error`` for details.
    """
    if parser is None:
        from skyknit.parser.parser import LLMPatternParser

        parser = LLMPatternParser()

    pi = ParserInput(
        pattern_text=pattern_text,
        gauge=gauge,
        stitch_motif=stitch_motif,
        yarn_spec=yarn_spec,
        precision=precision,
    )

    try:
        out = parser.parse(pi)
    except Exception as exc:
        return ValidationReport(
            passed=False,
            checker_result=None,
            parsed_pattern=None,
            parse_error=str(exc),
        )

    result = check_all(out.manifest, out.irs, out.constraints)
    return ValidationReport(
        passed=result.passed,
        checker_result=result,
        parsed_pattern=out.parsed_pattern,
        parse_error=None,
    )
