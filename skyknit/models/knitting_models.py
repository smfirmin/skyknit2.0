from dataclasses import dataclass
from enum import Enum


class ProjectType(Enum):
    BLANKET = "blanket"


class DifficultyLevel(Enum):
    """Difficulty levels for patterns and techniques"""

    BEGINNER = "beginner"
    EASY = "easy"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class YarnWeight(Enum):
    """Standard yarn weight categories"""

    FINGERING = "fingering"  # Weight 1
    SPORT = "sport"  # Weight 2
    DK = "dk"  # Weight 3
    WORSTED = "worsted"  # Weight 4
    ARAN = "aran"  # Weight 4.5
    BULKY = "bulky"  # Weight 5
    SUPER_BULKY = "super_bulky"  # Weight 6


@dataclass
class YarnSpec:
    weight: YarnWeight
    fiber: str  # wool, cotton, acrylic, etc.
    color: str | None = None  # for colorwork


@dataclass
class StitchPattern:
    name: str
    row_repeat: int
    stitch_repeat: int
    instructions: list[str]


@dataclass
class FabricSpec:
    stitch_pattern: StitchPattern
    yarn_requirements: YarnSpec
    gauge: dict[str, float]  # stitches per inch, rows per inch
    border_pattern: StitchPattern | None = None


@dataclass
class Dimensions:
    width: float  # inches
    length: float  # inches


@dataclass
class DesignSpec:
    project_type: ProjectType
    dimensions: Dimensions
    fabric: FabricSpec
    style_preferences: dict[str, str]  # texture, border, etc.
    special_requirements: list[str]


@dataclass
class PatternInstruction:
    step: int
    instruction: str
    stitch_count: int | None = None
    notes: str | None = None


@dataclass
class ConstructionZone:
    name: str  # "border", "main_body", "edging"
    relative_position: str  # "top", "bottom", "sides", "center"
    priority: int  # construction order


@dataclass
class ConstructionSpec:
    target_dimensions: Dimensions
    construction_zones: list[ConstructionZone]
    construction_sequence: list[
        str
    ]  # ordered steps: ["cast_on", "bottom_border", "main_body", "top_border", "bind_off"]
    finishing_requirements: list[str]  # ["blocking", "seaming", "edge_finishing"]
    structural_notes: list[str]  # construction-specific guidance


@dataclass
class PatternSpec:
    title: str
    instructions: list[PatternInstruction]
    materials: dict[str, str]
    gauge_info: dict[str, float]
    finished_dimensions: Dimensions
    estimated_yardage: int  # calculated based on dimensions and gauge
