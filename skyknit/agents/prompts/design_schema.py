"""
JSON Schema for design requirements extraction in the DesignAgent.

This schema defines the structure for extracting knitting project requirements
from natural language user requests.
"""

DESIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "project_type": {"type": "string", "enum": ["BLANKET"]},
        "dimensions": {
            "type": "object",
            "properties": {
                "width": {"type": "number", "minimum": 1},
                "length": {"type": "number", "minimum": 1},
            },
            "required": ["width", "length"],
        },
        "style_preferences": {
            "type": "object",
            "properties": {
                "texture": {"type": "string"},
                "complexity": {"type": "string"},
            },
        },
        "special_requirements": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "project_type",
        "dimensions",
        "style_preferences",
        "special_requirements",
    ],
}
