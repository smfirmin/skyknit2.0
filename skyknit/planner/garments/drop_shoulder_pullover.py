"""
Canonical GarmentSpec for a top-down drop-shoulder pullover.

Construction sequence (top-down, in-the-round):
  1. Body         — CYLINDER; cast on at neckline/shoulders, work down to hem.
                    Has two SELVEDGE armhole edges from which sleeves pick up.
  2. Left sleeve  — TRAPEZOID; stitches picked up from body's left armhole edge.
  3. Right sleeve — TRAPEZOID; mirror of left sleeve.

Drop shoulder topology differs from the yoke pullover:
  - No yoke component — body goes directly from shoulders to hem.
  - Sleeve attachment uses PICKUP joins (SELVEDGE → LIVE_STITCH), not CONTINUATION.
  - Body has 4 edges: neck (CAST_ON), hem (BOUND_OFF), and two SELVEDGE armhole edges.
  - SELVEDGE armhole edges carry no stitch count themselves; the PICKUP join's
    pickup_ratio governs how many stitches the sleeve picks up from the body depth.

Measurement keys required (all in mm):
  chest_circumference_mm
  body_length_mm
  sleeve_length_mm
  upper_arm_circumference_mm
  wrist_circumference_mm

ProportionSpec ratio keys used (all optional; default 1.0 if absent):
  body_ease     — multiplied with chest_circumference_mm
  sleeve_ease   — multiplied with upper_arm_circumference_mm
  wrist_ease    — multiplied with wrist_circumference_mm
"""

from __future__ import annotations

from skyknit.schemas.garment import (
    ComponentBlueprint,
    DimensionRule,
    EdgeSpec,
    GarmentSpec,
    JoinSpec,
)
from skyknit.schemas.manifest import Handedness, ShapeType
from skyknit.topology.types import EdgeType, JoinType

_REQUIRED_MEASUREMENTS: frozenset[str] = frozenset(
    {
        "chest_circumference_mm",
        "body_length_mm",
        "sleeve_length_mm",
        "upper_arm_circumference_mm",
        "wrist_circumference_mm",
    }
)

_BODY = ComponentBlueprint(
    name="body",
    shape_type=ShapeType.CYLINDER,
    handedness=Handedness.NONE,
    edges=(
        EdgeSpec(name="neck", edge_type=EdgeType.CAST_ON, join_id=None),
        EdgeSpec(name="hem", edge_type=EdgeType.BOUND_OFF, join_id=None),
        EdgeSpec(name="left_armhole", edge_type=EdgeType.SELVEDGE, join_id="j_left_armhole"),
        EdgeSpec(name="right_armhole", edge_type=EdgeType.SELVEDGE, join_id="j_right_armhole"),
    ),
    dimension_rules=(
        DimensionRule("circumference_mm", "chest_circumference_mm", "body_ease"),
        DimensionRule("depth_mm", "body_length_mm"),
    ),
)

_LEFT_SLEEVE = ComponentBlueprint(
    name="left_sleeve",
    shape_type=ShapeType.TRAPEZOID,
    handedness=Handedness.LEFT,
    edges=(
        EdgeSpec(name="top", edge_type=EdgeType.LIVE_STITCH, join_id="j_left_armhole"),
        EdgeSpec(name="cuff", edge_type=EdgeType.BOUND_OFF, join_id=None),
    ),
    dimension_rules=(
        DimensionRule("top_circumference_mm", "upper_arm_circumference_mm", "sleeve_ease"),
        DimensionRule("bottom_circumference_mm", "wrist_circumference_mm", "wrist_ease"),
        DimensionRule("depth_mm", "sleeve_length_mm"),
    ),
)

_RIGHT_SLEEVE = ComponentBlueprint(
    name="right_sleeve",
    shape_type=ShapeType.TRAPEZOID,
    handedness=Handedness.RIGHT,
    edges=(
        EdgeSpec(name="top", edge_type=EdgeType.LIVE_STITCH, join_id="j_right_armhole"),
        EdgeSpec(name="cuff", edge_type=EdgeType.BOUND_OFF, join_id=None),
    ),
    dimension_rules=(
        DimensionRule("top_circumference_mm", "upper_arm_circumference_mm", "sleeve_ease"),
        DimensionRule("bottom_circumference_mm", "wrist_circumference_mm", "wrist_ease"),
        DimensionRule("depth_mm", "sleeve_length_mm"),
    ),
)

_JOIN_LEFT_ARMHOLE = JoinSpec(
    id="j_left_armhole",
    join_type=JoinType.PICKUP,
    edge_a_ref="body.left_armhole",  # SELVEDGE (upstream / source)
    edge_b_ref="left_sleeve.top",  # LIVE_STITCH (downstream / receiving)
)

_JOIN_RIGHT_ARMHOLE = JoinSpec(
    id="j_right_armhole",
    join_type=JoinType.PICKUP,
    edge_a_ref="body.right_armhole",  # SELVEDGE (upstream / source)
    edge_b_ref="right_sleeve.top",  # LIVE_STITCH (downstream / receiving)
)


def make_drop_shoulder_pullover() -> GarmentSpec:
    """Return the canonical GarmentSpec for a top-down drop-shoulder pullover."""
    return GarmentSpec(
        garment_type="top-down-drop-shoulder-pullover",
        components=(_BODY, _LEFT_SLEEVE, _RIGHT_SLEEVE),
        joins=(_JOIN_LEFT_ARMHOLE, _JOIN_RIGHT_ARMHOLE),
        required_measurements=_REQUIRED_MEASUREMENTS,
    )


# Self-register so importing this module makes the factory discoverable.
from skyknit.planner.garments.registry import register  # noqa: E402

register("top-down-drop-shoulder-pullover", make_drop_shoulder_pullover)
