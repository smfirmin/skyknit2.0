"""
Operation and join prose templates for the TemplateWriter.

render_op converts a single Operation into pattern prose.
render_join_instruction converts a join template key and parameters into prose.
"""

from __future__ import annotations

from skyknit.schemas.ir import Operation, OpType
from skyknit.schemas.manifest import Handedness


def render_op(op: Operation) -> str:
    """Render a single knitting operation as pattern prose."""
    match op.op_type:
        case OpType.CAST_ON:
            count = op.parameters["count"]
            return f"Cast on {count} stitches."
        case OpType.WORK_EVEN:
            rows = op.row_count or 0
            count = op.stitch_count_after or 0
            return f"Work even for {rows} rows ({count} stitches)."
        case OpType.INCREASE_SECTION:
            count = op.stitch_count_after or 0
            rows = op.row_count or 0
            return f"Increase evenly to {count} sts over {rows} rows."
        case OpType.DECREASE_SECTION:
            count = op.stitch_count_after or 0
            rows = op.row_count or 0
            return f"Decrease to {count} sts over {rows} rows."
        case OpType.TAPER:
            count = op.stitch_count_after or 0
            rows = op.row_count or 0
            return f"Decrease to {count} sts over {rows} rows."
        case OpType.BIND_OFF:
            count = op.parameters.get("count", 0)
            return f"Bind off {count} stitches."
        case OpType.HOLD:
            count = op.parameters["count"]
            label = op.parameters["label"]
            return f"Place {count} sts on holder for {label}."
        case OpType.SEPARATE:
            count = op.parameters["count"]
            label = op.parameters["label"]
            return f"Place {count} sts on holder for {label}."
        case OpType.PICKUP_STITCHES:
            count = op.parameters.get("count", op.stitch_count_after or 0)
            return f"Pick up and knit {count} stitches."
        case _:
            return f"[{op.op_type.value}]"


def _side_label(handedness: Handedness) -> str:
    """Return 'left', 'right', or '' based on handedness."""
    if handedness == Handedness.LEFT:
        return "left"
    if handedness == Handedness.RIGHT:
        return "right"
    return ""


def render_join_instruction(
    template_key: str,
    join_params: dict[str, object],
    other_component: str,
    handedness: Handedness,
    stitch_count: int = 0,
) -> str:
    """
    Render a join instruction as pattern prose.

    Parameters
    ----------
    template_key:
        Key from writer_dispatch.yaml (e.g. ``"pickup_block"``).
    join_params:
        Join parameters dict (from Join.parameters, converted to mutable dict).
    other_component:
        The name of the other component involved in the join.
    handedness:
        Handedness of the component being rendered.
    stitch_count:
        Relevant stitch count for the instruction (e.g. pickup count).
    """
    side = _side_label(handedness)
    side_prefix = f"{side} " if side else ""

    match template_key:
        case "continuation_inline":
            return ""
        case "held_stitch_block":
            return f"Place next {stitch_count} sts on holder for {other_component}."
        case "cast_on_join_block":
            method = str(join_params.get("cast_on_method", "backward loop"))
            count = int(join_params.get("cast_on_count") or stitch_count)
            return f"Using {method}, cast on {count} stitches."
        case "pickup_block":
            return f"Pick up and knit {stitch_count} sts along {side_prefix}armhole edge."
        case "seam_note":
            return f"Seam {side_prefix}edge to {other_component} using mattress stitch."
        case "three_needle_block":
            return f"Join to {other_component} using three-needle bind-off."
        case _:
            return f"[{template_key}]"
