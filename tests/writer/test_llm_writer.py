"""
Tests for skyknit/writer/llm_writer.py — LLMWriter.

Unit tests (CI-safe) mock the anthropic client via unittest.mock so no real
API calls are made.  Integration tests require ANTHROPIC_API_KEY and are
skipped in CI.
"""

from __future__ import annotations

import os
import sys
from types import MappingProxyType
from unittest.mock import MagicMock

import pytest

import skyknit.planner.garments  # noqa: F401 — triggers garment registration
from skyknit.fabric.module import FabricInput
from skyknit.orchestrator.pipeline import DeterministicOrchestrator, OrchestratorInput
from skyknit.planner.garments.registry import get
from skyknit.schemas.constraint import StitchMotif, YarnSpec
from skyknit.schemas.proportion import PrecisionPreference, ProportionSpec
from skyknit.utilities.types import Gauge
from skyknit.writer.writer import PatternWriter, WriterInput, WriterOutput

# ── Shared fixtures ────────────────────────────────────────────────────────────

_GAUGE = Gauge(stitches_per_inch=20.0, rows_per_inch=28.0)
_MOTIF = StitchMotif(name="stockinette", stitch_repeat=1, row_repeat=1)
_YARN = YarnSpec(weight="DK", fiber="wool", needle_size_mm=4.0)

_PROPORTION = ProportionSpec(
    ratios=MappingProxyType({"body_ease": 1.08, "sleeve_ease": 1.1, "wrist_ease": 1.05}),
    precision=PrecisionPreference.MEDIUM,
)
_FABRIC = FabricInput(
    component_names=(),
    gauge=_GAUGE,
    stitch_motif=_MOTIF,
    yarn_spec=_YARN,
    precision=PrecisionPreference.MEDIUM,
)
_MEASUREMENTS = {
    "chest_circumference_mm": 914.4,
    "body_length_mm": 457.2,
    "sleeve_length_mm": 495.3,
    "upper_arm_circumference_mm": 381.0,
    "wrist_circumference_mm": 152.4,
}


def _drop_shoulder_writer_input() -> WriterInput:
    oi = OrchestratorInput(
        garment_spec=get("top-down-drop-shoulder-pullover"),
        proportion_spec=_PROPORTION,
        measurements=_MEASUREMENTS,
        fabric_input=_FABRIC,
    )
    out = DeterministicOrchestrator().run(oi)
    return WriterInput(manifest=out.manifest, irs=out.irs, component_order=out.component_order)


def _make_mock_client(sections: dict[str, str]) -> MagicMock:
    """Return a mock anthropic.Anthropic() that yields a tool_use block with given sections."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"sections": sections}
    response = MagicMock()
    response.content = [tool_block]
    client = MagicMock()
    client.messages.create.return_value = response
    return client


def _make_llm_writer_with_mock(sections: dict[str, str], **kwargs):
    """Instantiate LLMWriter with a mocked anthropic client."""
    from skyknit.writer.llm_writer import LLMWriter

    with _patch_anthropic():
        writer = LLMWriter(**kwargs)
    writer._client = _make_mock_client(sections)
    return writer


def _patch_anthropic():
    """Context manager that injects a minimal anthropic stub into sys.modules."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = MagicMock()
        original = sys.modules.get("anthropic")  # save before any mutation
        sys.modules["anthropic"] = mock_anthropic
        try:
            yield mock_anthropic
        finally:
            if original is None:
                sys.modules.pop("anthropic", None)
            else:
                sys.modules["anthropic"] = original

    return _ctx()


# ── TestLLMWriter ──────────────────────────────────────────────────────────────


class TestLLMWriter:
    def _wi(self) -> WriterInput:
        return _drop_shoulder_writer_input()

    def test_write_returns_writer_output(self):
        wi = self._wi()
        enhanced = {name: f"Enhanced section: {name}" for name in wi.component_order}
        writer = _make_llm_writer_with_mock(enhanced)
        out = writer.write(wi)
        assert isinstance(out, WriterOutput)

    def test_all_sections_present(self):
        wi = self._wi()
        enhanced = {name: f"Enhanced: {name}" for name in wi.component_order}
        writer = _make_llm_writer_with_mock(enhanced)
        out = writer.write(wi)
        assert set(out.sections.keys()) == set(wi.component_order)

    def test_component_order_preserved_in_full_pattern(self):
        wi = self._wi()
        # Each section has a unique marker matching its position
        enhanced = {name: f"SECTION_{i}" for i, name in enumerate(wi.component_order)}
        writer = _make_llm_writer_with_mock(enhanced)
        out = writer.write(wi)
        positions = [out.full_pattern.index(f"SECTION_{i}") for i in range(len(wi.component_order))]
        assert positions == sorted(positions)

    def test_missing_section_falls_back_to_template(self):
        """If LLM omits a section, template prose is used for that section."""
        from skyknit.writer.writer import TemplateWriter

        wi = self._wi()
        template_out = TemplateWriter().write(wi)
        # LLM returns only the first section
        first = wi.component_order[0]
        partial = {first: "LLM-enhanced body only"}
        writer = _make_llm_writer_with_mock(partial)
        out = writer.write(wi)
        # First section: LLM version
        assert out.sections[first] == "LLM-enhanced body only"
        # Remaining sections: template version
        for name in wi.component_order[1:]:
            assert out.sections[name] == template_out.sections[name]

    def test_no_tool_block_falls_back_to_template(self):
        """If Claude returns no tool_use block, return TemplateWriter output."""
        from skyknit.writer.writer import TemplateWriter

        wi = self._wi()
        response = MagicMock()
        response.content = []  # no tool_use block
        client = MagicMock()
        client.messages.create.return_value = response

        with _patch_anthropic():
            from skyknit.writer.llm_writer import LLMWriter

            writer = LLMWriter()
        writer._client = client

        out = writer.write(wi)
        template_out = TemplateWriter().write(wi)
        assert out.full_pattern == template_out.full_pattern

    def test_api_exception_falls_back_to_template(self):
        """If the API call raises, return TemplateWriter output with a warning."""
        from skyknit.writer.writer import TemplateWriter

        wi = self._wi()
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("network error")

        with _patch_anthropic():
            from skyknit.writer.llm_writer import LLMWriter

            writer = LLMWriter()
        writer._client = client

        with pytest.warns(UserWarning, match="LLMWriter failed"):
            out = writer.write(wi)
        template_out = TemplateWriter().write(wi)
        assert out.full_pattern == template_out.full_pattern

    def test_context_included_when_gauge_provided(self):
        """Gauge context must appear in the user message when gauge is set."""
        wi = self._wi()
        enhanced = {name: f"Enhanced: {name}" for name in wi.component_order}
        writer = _make_llm_writer_with_mock(enhanced, gauge=_GAUGE)
        writer.write(wi)
        call_kwargs = writer._client.messages.create.call_args
        user_content = call_kwargs[1]["messages"][0]["content"]
        assert "20.0 stitches" in user_content
        assert "28.0 rows" in user_content

    def test_no_context_when_none_passed(self):
        """No context prefix when gauge, motif, and yarn are all None."""
        from skyknit.writer.writer import TemplateWriter

        wi = self._wi()
        template_out = TemplateWriter().write(wi)
        enhanced = {name: template_out.sections[name] for name in wi.component_order}
        writer = _make_llm_writer_with_mock(enhanced)  # no gauge/motif/yarn
        writer.write(wi)
        call_kwargs = writer._client.messages.create.call_args
        user_content = call_kwargs[1]["messages"][0]["content"]
        # User message should start directly with pattern text (first section header)
        assert user_content.startswith(wi.component_order[0].replace("_", " ").title())

    def test_llm_writer_satisfies_pattern_writer_protocol(self):
        with _patch_anthropic():
            from skyknit.writer.llm_writer import LLMWriter

            writer = LLMWriter()
        assert isinstance(writer, PatternWriter)

    def test_import_error_without_anthropic(self):
        """LLMWriter raises ImportError if anthropic is not installed."""
        import importlib
        from unittest.mock import patch

        import skyknit.writer.llm_writer as llm_mod

        with patch.dict(sys.modules, {"anthropic": None}):  # type: ignore[dict-item]
            importlib.reload(llm_mod)
            with pytest.raises(ImportError, match="uv add anthropic"):
                llm_mod.LLMWriter()

        # Restore the module to its normal state after the test.
        importlib.reload(llm_mod)


# ── Integration tests (skipped in CI) ─────────────────────────────────────────

_SKIP_LLM = pytest.mark.skipif(
    os.environ.get("ANTHROPIC_API_KEY") is None,
    reason="ANTHROPIC_API_KEY not set — LLM integration tests skipped",
)


@_SKIP_LLM
def test_llm_writer_drop_shoulder():
    """LLMWriter produces a non-empty pattern that parses back through check_all()."""
    from skyknit.api.validate import validate_pattern
    from skyknit.writer.llm_writer import LLMWriter

    wi = _drop_shoulder_writer_input()
    writer = LLMWriter(gauge=_GAUGE, stitch_motif=_MOTIF, yarn_spec=_YARN)
    out = writer.write(wi)
    assert out.full_pattern.strip()
    report = validate_pattern(out.full_pattern, _GAUGE, _MOTIF, _YARN)
    assert report.passed, f"Round-trip failed:\n{report.parse_error}\n{report.checker_result}"


@_SKIP_LLM
def test_llm_writer_differs_from_template():
    """LLM output should produce richer prose than the mechanical template."""
    from skyknit.writer.llm_writer import LLMWriter
    from skyknit.writer.writer import TemplateWriter

    wi = _drop_shoulder_writer_input()
    template_out = TemplateWriter().write(wi)
    llm_out = LLMWriter(gauge=_GAUGE, stitch_motif=_MOTIF, yarn_spec=_YARN).write(wi)
    assert llm_out.full_pattern != template_out.full_pattern
