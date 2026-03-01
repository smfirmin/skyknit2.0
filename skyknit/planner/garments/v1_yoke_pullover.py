"""
Canonical GarmentSpec for a v1 top-down yoke pullover.

Construction sequence (top-down, in-the-round):
  1. Yoke  — CYLINDER; cast on at neckline, increase to full chest width
  2. Body  — CYLINDER; picks up yoke stitches via CONTINUATION, works down to hem
  3. Left sleeve  — TRAPEZOID; tapers from upper arm to wrist (standalone for v1)
  4. Right sleeve — TRAPEZOID; mirror of left sleeve (standalone for v1)

Yoke → body join: CONTINUATION (LIVE_STITCH → LIVE_STITCH).
Sleeve joins (armhole → sleeve top) are deferred to a future phase — they require
per-edge dimension routing beyond v1 scope.

Measurement keys required (all in mm):
  chest_circumference_mm
  body_length_mm
  yoke_depth_mm
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
        "yoke_depth_mm",
        "sleeve_length_mm",
        "upper_arm_circumference_mm",
        "wrist_circumference_mm",
    }
)

_YOKE = ComponentBlueprint(
    name="yoke",
    shape_type=ShapeType.CYLINDER,
    handedness=Handedness.NONE,
    edges=(
        EdgeSpec(name="neck", edge_type=EdgeType.CAST_ON, join_id=None),
        EdgeSpec(name="body_join", edge_type=EdgeType.LIVE_STITCH, join_id="j_yoke_body"),
    ),
    dimension_rules=(
        DimensionRule("circumference_mm", "chest_circumference_mm", "body_ease"),
        DimensionRule("depth_mm", "yoke_depth_mm"),
    ),
)

_BODY = ComponentBlueprint(
    name="body",
    shape_type=ShapeType.CYLINDER,
    handedness=Handedness.NONE,
    edges=(
        EdgeSpec(name="top", edge_type=EdgeType.LIVE_STITCH, join_id="j_yoke_body"),
        EdgeSpec(name="hem", edge_type=EdgeType.BOUND_OFF, join_id=None),
    ),
    dimension_rules=(
        # Same circumference formula as yoke → stitch counts match → CONTINUATION join validates
        DimensionRule("circumference_mm", "chest_circumference_mm", "body_ease"),
        DimensionRule("depth_mm", "body_length_mm"),
    ),
)

_LEFT_SLEEVE = ComponentBlueprint(
    name="left_sleeve",
    shape_type=ShapeType.TRAPEZOID,
    handedness=Handedness.LEFT,
    edges=(
        EdgeSpec(name="top", edge_type=EdgeType.LIVE_STITCH, join_id=None),
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
        EdgeSpec(name="top", edge_type=EdgeType.LIVE_STITCH, join_id=None),
        EdgeSpec(name="cuff", edge_type=EdgeType.BOUND_OFF, join_id=None),
    ),
    dimension_rules=(
        DimensionRule("top_circumference_mm", "upper_arm_circumference_mm", "sleeve_ease"),
        DimensionRule("bottom_circumference_mm", "wrist_circumference_mm", "wrist_ease"),
        DimensionRule("depth_mm", "sleeve_length_mm"),
    ),
)

_JOIN_YOKE_BODY = JoinSpec(
    id="j_yoke_body",
    join_type=JoinType.CONTINUATION,
    edge_a_ref="yoke.body_join",
    edge_b_ref="body.top",
)


def make_v1_yoke_pullover() -> GarmentSpec:
    """Return the canonical GarmentSpec for a v1 top-down yoke pullover."""
    return GarmentSpec(
        garment_type="top-down-yoke-pullover",
        components=(_YOKE, _BODY, _LEFT_SLEEVE, _RIGHT_SLEEVE),
        joins=(_JOIN_YOKE_BODY,),
        required_measurements=_REQUIRED_MEASUREMENTS,
    )


# Self-register so importing this module makes the factory discoverable.
from skyknit.planner.garments.registry import register  # noqa: E402

register("top-down-yoke-pullover", make_v1_yoke_pullover)
