"""
TemplateWriter — converts assembled ComponentIRs into pattern prose.

Pipeline (for each component in topological order from component_order):
  1. Renders a section header with the component display name.
  2. Appends HEADER_NOTE join instructions to the header line.
  3. Prepends INSTRUCTION join instructions (where this component is edge_b)
     at the start of the section body.
  4. Translates each Operation to prose via templates.

All sections are concatenated into full_pattern in component_order sequence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from skyknit.schemas.ir import ComponentIR, OpType
from skyknit.schemas.manifest import ShapeManifest
from skyknit.topology.registry import get_registry
from skyknit.topology.types import JoinType, RenderingMode
from skyknit.writer.templates import render_join_instruction, render_op


@dataclass(frozen=True)
class WriterInput:
    """Complete input bundle for the TemplateWriter."""

    manifest: ShapeManifest
    irs: dict[str, ComponentIR]
    component_order: list[str]


@dataclass(frozen=True)
class WriterOutput:
    """Output of a successful pattern write."""

    sections: dict[str, str]  # component name → section text
    full_pattern: str  # all sections concatenated in component_order


@runtime_checkable
class PatternWriter(Protocol):
    """Protocol for pattern writers."""

    def write(self, writer_input: WriterInput) -> WriterOutput: ...


class TemplateWriter:
    """
    Deterministic template-based writer.

    Uses the TopologyRegistry writer_dispatch table to determine how each join
    type renders.  Respects Handedness for directional joins (PICKUP, HELD_STITCH).
    """

    def write(self, wi: WriterInput) -> WriterOutput:
        """
        Convert all ComponentIRs into pattern prose sections.

        Parameters
        ----------
        wi:
            WriterInput bundle (manifest, IRs, and topological component order).

        Returns
        -------
        WriterOutput
            Per-component section text and the full concatenated pattern.
        """
        registry = get_registry()
        sections: dict[str, str] = {}

        for comp_name in wi.component_order:
            comp_spec = next(c for c in wi.manifest.components if c.name == comp_name)
            ir = wi.irs[comp_name]
            handedness = comp_spec.handedness

            header_notes: list[str] = []
            instructions_before: list[str] = []

            for join in wi.manifest.joins:
                dispatch = registry.get_writer_dispatch(join.join_type)
                comp_is_downstream = join.edge_b_ref.split(".")[0] == comp_name
                comp_is_upstream = join.edge_a_ref.split(".")[0] == comp_name

                if not (comp_is_downstream or comp_is_upstream):
                    continue

                if dispatch.rendering_mode == RenderingMode.HEADER_NOTE:
                    # SEAM joins: add a finishing note to both component headers.
                    other = (
                        join.edge_a_ref.split(".")[0]
                        if comp_is_downstream
                        else join.edge_b_ref.split(".")[0]
                    )
                    note = render_join_instruction(
                        dispatch.template_key,
                        dict(join.parameters),
                        other,
                        handedness,
                        stitch_count=ir.starting_stitch_count,
                    )
                    if note:
                        header_notes.append(note)

                elif dispatch.rendering_mode == RenderingMode.INSTRUCTION and comp_is_downstream:
                    # PICKUP / HELD_STITCH / CAST_ON_JOIN: emit at start of downstream section.
                    instruction = render_join_instruction(
                        dispatch.template_key,
                        dict(join.parameters),
                        join.edge_a_ref.split(".")[0],
                        handedness,
                        stitch_count=ir.starting_stitch_count,
                    )
                    if instruction:
                        instructions_before.append(instruction)

                # INLINE (CONTINUATION) → nothing to emit.

            # If a PICKUP join instruction was emitted for this component (as downstream),
            # the IR's first CAST_ON represents the same pickup action — skip it to avoid
            # redundant prose like "Cast on 330 stitches." immediately after "Pick up...".
            skip_leading_cast_on = any(
                registry.get_writer_dispatch(j.join_type).rendering_mode
                == RenderingMode.INSTRUCTION
                and j.join_type == JoinType.PICKUP
                and j.edge_b_ref.split(".")[0] == comp_name
                for j in wi.manifest.joins
            )

            # Build section text.
            lines: list[str] = []
            display_name = comp_name.replace("_", " ").title()
            header = display_name
            if header_notes:
                header += " — " + "; ".join(header_notes)
            lines.append(header)
            lines.extend(instructions_before)
            for op in ir.operations:
                if skip_leading_cast_on and op.op_type == OpType.CAST_ON:
                    skip_leading_cast_on = False
                    continue
                prose = render_op(op)
                if prose:
                    lines.append(prose)

            sections[comp_name] = "\n".join(lines)

        full_pattern = "\n\n".join(sections[name] for name in wi.component_order)
        return WriterOutput(sections=sections, full_pattern=full_pattern)
