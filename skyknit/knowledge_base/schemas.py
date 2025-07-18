"""
Database schemas for the knitting pattern knowledge base.

This module defines the data structures for storing stitch patterns
and yarn information that will be used by LLM-powered agents.
"""

from dataclasses import dataclass, field

from skyknit.models.knitting_models import DifficultyLevel, YarnWeight


@dataclass
class StitchPattern:
    """Comprehensive stitch pattern definition for structured database"""

    id: str
    name: str
    category: str  # "basic", "cable", "lace", "colorwork", "textured", "ribbing"
    difficulty: DifficultyLevel

    # Pattern definition
    repeat_width: int  # stitches in pattern repeat
    repeat_height: int  # rows in pattern repeat
    instructions: list[str]  # row-by-row instructions
    chart: str | None = None  # ASCII or symbol chart

    # Gauge and sizing
    gauge_modifier: float = 1.0  # multiplier for base gauge
    recommended_yarn_weights: list[YarnWeight] = field(default_factory=list)

    # Construction properties
    lies_flat: bool = True  # does pattern create a flat fabric
    has_curl: bool = False  # does pattern curl at edges
    stretch_horizontal: float = 1.0  # stretch factor width-wise
    stretch_vertical: float = 1.0  # stretch factor height-wise

    # Usage recommendations
    best_for: list[str] = field(
        default_factory=list
    )  # "blankets", "scarves", "sweaters"
    combines_well_with: list[str] = field(default_factory=list)  # other pattern IDs

    # Technical details
    stitch_count_multiple: int = 1  # cast-on must be multiple of this
    edge_stitches_needed: int = 0  # extra stitches for pattern edges
    requires_border: bool = False  # pattern needs border for stability

    # Metadata
    description: str = ""
    tips: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    variations: list[str] = field(default_factory=list)

    # RAG support
    embedding: list[float] | None = None  # vector embedding for semantic search
    keywords: list[str] = field(default_factory=list)  # searchable keywords


@dataclass
class YarnInfo:
    """Comprehensive yarn information for structured database"""

    id: str
    name: str
    brand: str
    weight: YarnWeight

    # Fiber composition
    fiber_content: dict[str, float]  # {"wool": 0.8, "nylon": 0.2}
    fiber_type: str  # "natural", "synthetic", "blend"

    # Physical properties
    yardage_per_unit: int  # yards per skein/ball
    unit_weight_grams: int  # grams per skein/ball
    recommended_needle_size: str  # "US 8" or "5.0mm"

    # Gauge information
    standard_gauge_stitches: int  # stitches per 4 inches
    standard_gauge_rows: int  # rows per 4 inches
    gauge_needle_size: str  # needle size for standard gauge

    # Care instructions
    care_instructions: list[str] = field(default_factory=list)
    machine_washable: bool = False
    superwash: bool = False

    # Working properties
    ease_of_working: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    drape: str = "medium"  # "stiff", "medium", "drapey"
    warmth: str = "medium"  # "cool", "medium", "warm", "very_warm"
    durability: str = "medium"  # "delicate", "medium", "durable"

    # Availability and cost
    price_range: str = "medium"  # "budget", "medium", "premium", "luxury"
    availability: str = "common"  # "rare", "limited", "common", "discontinued"
    colors_available: list[str] = field(default_factory=list)

    # Pattern compatibility
    best_for_patterns: list[str] = field(default_factory=list)  # pattern categories
    not_recommended_for: list[str] = field(default_factory=list)

    # RAG support
    embedding: list[float] | None = None
    keywords: list[str] = field(default_factory=list)


@dataclass
class ConstructionTechnique:
    """Construction methods and techniques"""

    id: str
    name: str
    category: str  # "cast_on", "bind_off", "joining", "shaping", "finishing"
    difficulty: DifficultyLevel

    # Usage
    best_for: list[str] = field(default_factory=list)  # project types
    yarn_suitability: list[YarnWeight] = field(default_factory=list)

    # Instructions
    description: str = ""
    step_by_step: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)

    # Alternatives
    alternatives: list[str] = field(default_factory=list)  # other technique IDs

    # RAG support
    embedding: list[float] | None = None
    keywords: list[str] = field(default_factory=list)
