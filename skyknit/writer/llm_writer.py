"""
LLMWriter — two-pass LLM-enhanced pattern writer.

Pass 1 (deterministic): TemplateWriter generates correct, complete prose with
exact stitch/row counts — the ground truth.

Pass 2 (LLM): Claude receives the template prose and rewrites it into richer,
more idiomatic knitting language via the write_knitting_pattern tool.  The LLM
cannot change any number because the template prose already states them; any
deviation would be a factual error the knitter could detect.

On any failure (network error, no tool_use block, malformed JSON, missing section),
write() returns the TemplateWriter output unchanged — the caller always gets a
usable pattern.

LLMWriter satisfies the PatternWriter Protocol and is a drop-in replacement for
TemplateWriter in generate_pattern() or any other pipeline that accepts a writer.

Requires the ``anthropic`` package (``uv add anthropic`` or
``pip install skyknit[llm]``).  The import is deferred to ``__init__`` so the
rest of the module is importable without the package installed.
"""

from __future__ import annotations

import warnings

from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.utilities.types import Gauge
from skyknit.writer.prompts import LLM_WRITER_TOOL_SCHEMA, SYSTEM_PROMPT
from skyknit.writer.writer import TemplateWriter, WriterInput, WriterOutput


def _build_context(
    gauge: Gauge | None,
    stitch_motif: StitchMotif | None,
    yarn_spec: YarnSpec | None,
) -> str:
    """Build an optional context block for the LLM user message prefix.

    Returns an empty string when all three arguments are None, so the caller
    can test truthiness before prepending.
    """
    parts: list[str] = []
    if gauge:
        parts.append(
            f"Gauge: {gauge.stitches_per_inch} stitches and {gauge.rows_per_inch} rows per inch."
        )
    if yarn_spec:
        parts.append(
            f"Yarn: {yarn_spec.weight} weight, {yarn_spec.fiber}, "
            f"{yarn_spec.needle_size_mm} mm needles."
        )
    if stitch_motif:
        parts.append(f"Stitch pattern: {stitch_motif.name}.")
    return "\n".join(parts)


class LLMWriter:
    """
    Two-pass LLM-enhanced pattern writer.

    Satisfies the PatternWriter Protocol: accepts WriterInput, returns WriterOutput.

    Optional context (gauge, stitch_motif, yarn_spec) set at construction time
    enriches the LLM prompt so it can include physical-measurement conversions
    and yarn-appropriate language.  All three are optional; omitting them still
    produces richer prose — just without measurement approximations.

    The Anthropic client reads ``ANTHROPIC_API_KEY`` from the environment.
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 4096,
        gauge: Gauge | None = None,
        stitch_motif: StitchMotif | None = None,
        yarn_spec: YarnSpec | None = None,
    ) -> None:
        try:
            import anthropic

            self._client = anthropic.Anthropic()
        except ImportError as exc:
            raise ImportError(
                "Install the LLM extras for writer support: uv add anthropic"
            ) from exc
        self._model = model
        self._max_tokens = max_tokens
        self._gauge = gauge
        self._stitch_motif = stitch_motif
        self._yarn_spec = yarn_spec
        self._template_writer = TemplateWriter()

    def write(self, wi: WriterInput) -> WriterOutput:
        """
        Enhance template prose with LLM rewriting.

        Falls back to TemplateWriter output with a UserWarning on any LLM failure.
        """
        template_out = self._template_writer.write(wi)

        context = _build_context(self._gauge, self._stitch_motif, self._yarn_spec)
        user_content = (
            (context + "\n\n" + template_out.full_pattern) if context else template_out.full_pattern
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                tools=[LLM_WRITER_TOOL_SCHEMA],
                tool_choice={"type": "any"},
                messages=[{"role": "user", "content": user_content}],
            )
            tool_block = next((b for b in response.content if b.type == "tool_use"), None)
            if tool_block is None:
                return template_out

            raw_sections: dict[str, str] = tool_block.input["sections"]
            # Fall back to template prose for any section the LLM omitted.
            sections = {
                name: raw_sections.get(name, template_out.sections[name])
                for name in wi.component_order
            }
            full_pattern = "\n\n".join(sections[name] for name in wi.component_order)
            return WriterOutput(sections=sections, full_pattern=full_pattern)
        except Exception as exc:  # noqa: BLE001 — intentional broad catch for graceful fallback
            warnings.warn(
                f"LLMWriter failed, returning template prose: {exc}",
                stacklevel=2,
            )
            return template_out
