"""
System prompt and tool schema for the LLM pattern parser.

SYSTEM_PROMPT is the semantic inverse of writer/templates.py: every prose
template in the Writer has a corresponding extraction rule here.

EXTRACT_TOOL_SCHEMA defines the single Claude tool used for structured output.
tool_choice={"type": "any"} in the API call forces Claude to call this tool,
guaranteeing JSON output rather than free-text prose.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are a knitting pattern analyzer. Extract the structural
components, operations, and joins from a knitting pattern into the tool schema.

## Operation mapping (prose → op_type)

"Cast on N stitches."
  → op_type=CAST_ON, parameters={"count": N}, stitch_count_after=N, row_count=null

"Work even for R rows (N stitches)."
  → op_type=WORK_EVEN, parameters={}, stitch_count_after=N, row_count=R

"Increase evenly to N sts over R rows."
  → op_type=INCREASE_SECTION, parameters={}, stitch_count_after=N, row_count=R

"Decrease to N sts over R rows."
  → op_type=DECREASE_SECTION, parameters={}, stitch_count_after=N, row_count=R
  NOTE: use TAPER (not DECREASE_SECTION) when the prose says "taper" or describes
  a gradual sleeve narrowing with explicit shaping intervals (e.g. "decrease 1 st
  each end every N rows R times"). Both map identically in the validator.

"Bind off N stitches."
  → op_type=BIND_OFF, parameters={"count": N}, stitch_count_after=0, row_count=null

"Pick up and knit N sts along [left/right] armhole edge."
  → op_type=PICKUP_STITCHES in the component's operations,
    parameters={"count": N}, stitch_count_after=N, row_count=null
  ALSO creates a PICKUP join (see Join rules below)

"Place N sts on holder for X."
  → op_type=HOLD (or SEPARATE), parameters={"count": N, "label": "X"},
    stitch_count_after=N (stitches placed aside; component may continue with remaining)

## Join inference

PICKUP joins: When a sleeve section opens with "Pick up and knit N sts along
[left/right] armhole edge," infer a PICKUP join:
  - id: "j_{side}_armhole" (e.g. "j_left_armhole")
  - join_type: "PICKUP"
  - edge_a_ref: "body.{side}_armhole" (the body's side edge — SELVEDGE type)
  - edge_b_ref: "{sleeve_name}.top" (e.g. "left_sleeve.top" — LIVE_STITCH type)
  - parameters: {} (pickup_ratio inferred from topology, not in prose)

CONTINUATION joins: When a section begins with live stitches passed directly from
a prior section (no cast-on, no pick-up — the prior section did not bind off), infer
a CONTINUATION join:
  - Example: Yoke ends without binding off, Body section continues from those stitches.
  - id: "j_{upstream}_{downstream}" (e.g. "j_yoke_body")
  - join_type: "CONTINUATION"
  - edge_a_ref: "{upstream}.{edge}" (e.g. "yoke.body_join")
  - edge_b_ref: "{downstream}.top" (e.g. "body.top")
  - parameters: {}

HELD_STITCH joins: When "Place N sts on holder for X" appears in one section and
those stitches are later resumed in another section, infer a HELD_STITCH join:
  - id: "j_held_{label}" (e.g. "j_held_neckline")
  - join_type: "HELD_STITCH"
  - edge_a_ref: "{source_component}.{holder_edge}"
  - edge_b_ref: "{dest_component}.{resume_edge}"
  - parameters: {}

SEAM joins: When "Seam [side] edge to [component]" appears in a section header
or inline, infer a SEAM join between the two named components.

## Handedness

"Left Sleeve" or any section with "left" in name → handedness="LEFT"
"Right Sleeve" or any section with "right" in name → handedness="RIGHT"
Everything else (Body, Yoke, etc.) → handedness="NONE"

## Name normalization

Convert display names to snake_case:
"Body" → "body"
"Left Sleeve" → "left_sleeve"
"Right Sleeve" → "right_sleeve"
"Yoke" → "yoke"

## Stitch counts

starting_stitch_count = stitch_count_after of the first operation
  EXCEPTION: if the first operation is PICKUP_STITCHES, use starting_stitch_count=0
  (the component starts with zero live stitches before the pick-up creates them;
  the parser enforces this automatically if the LLM reports a different value)
ending_stitch_count = 0 for any component whose last operation is BIND_OFF
                    = stitch_count_after of last op otherwise
"""

EXTRACT_TOOL_SCHEMA: dict = {
    "name": "extract_knitting_pattern",
    "description": (
        "Extract the structural components, operations, and joins from a knitting pattern."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "components": {
                "type": "array",
                "description": "One entry per named section in the pattern.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "snake_case component name, e.g. 'body', 'left_sleeve'",
                        },
                        "handedness": {
                            "type": "string",
                            "enum": ["LEFT", "RIGHT", "NONE"],
                        },
                        "starting_stitch_count": {
                            "type": "integer",
                            "description": "Live stitch count at start of this component",
                        },
                        "ending_stitch_count": {
                            "type": "integer",
                            "description": "Live stitch count at end (0 if bound off)",
                        },
                        "operations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "op_type": {
                                        "type": "string",
                                        "enum": [
                                            "CAST_ON",
                                            "WORK_EVEN",
                                            "INCREASE_SECTION",
                                            "DECREASE_SECTION",
                                            "TAPER",
                                            "BIND_OFF",
                                            "HOLD",
                                            "SEPARATE",
                                            "PICKUP_STITCHES",
                                        ],
                                    },
                                    "stitch_count_after": {"type": ["integer", "null"]},
                                    "row_count": {"type": ["integer", "null"]},
                                    "parameters": {
                                        "type": "object",
                                        "description": (
                                            '{"count": N} for CAST_ON/BIND_OFF/PICKUP_STITCHES; '
                                            "{} for WORK_EVEN/INCREASE_SECTION/DECREASE_SECTION/TAPER; "
                                            '{"count": N, "label": "X"} for HOLD/SEPARATE'
                                        ),
                                    },
                                },
                                "required": ["op_type", "stitch_count_after", "parameters"],
                            },
                        },
                    },
                    "required": [
                        "name",
                        "handedness",
                        "starting_stitch_count",
                        "ending_stitch_count",
                        "operations",
                    ],
                },
            },
            "joins": {
                "type": "array",
                "description": "Inter-component connections inferred from the pattern.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique join ID, e.g. 'j_left_armhole'",
                        },
                        "join_type": {
                            "type": "string",
                            "enum": [
                                "CONTINUATION",
                                "HELD_STITCH",
                                "CAST_ON_JOIN",
                                "PICKUP",
                                "SEAM",
                            ],
                        },
                        "edge_a_ref": {
                            "type": "string",
                            "description": "'component.edge_name', e.g. 'body.left_armhole'",
                        },
                        "edge_b_ref": {
                            "type": "string",
                            "description": "'component.edge_name', e.g. 'left_sleeve.top'",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Join-specific: {} for most; pickup_ratio for PICKUP",
                        },
                    },
                    "required": ["id", "join_type", "edge_a_ref", "edge_b_ref", "parameters"],
                },
            },
            "gauge": {
                "type": ["object", "null"],
                "description": "Gauge if stated in pattern, else null.",
                "properties": {
                    "stitches_per_inch": {"type": "number"},
                    "rows_per_inch": {"type": "number"},
                },
            },
            "garment_type_hint": {
                "type": ["string", "null"],
                "description": "Best guess at garment type if inferable, else null.",
            },
        },
        "required": ["components", "joins"],
    },
}
