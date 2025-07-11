from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ProjectType(Enum):
    BLANKET = "blanket"


@dataclass
class YarnSpec:
    weight: str  # DK, worsted, chunky, etc.
    fiber: str  # wool, cotton, acrylic, etc.
    color: Optional[str] = None  # for colorwork


@dataclass
class Dimensions:
    width: float  # inches
    length: float  # inches


@dataclass
class RequirementsSpec:
    project_type: ProjectType
    dimensions: Dimensions
    style_preferences: Dict[str, str]  # texture, border, etc.
    special_requirements: List[str]


@dataclass
class StitchPattern:
    name: str
    row_repeat: int
    stitch_repeat: int
    instructions: List[str]


@dataclass
class FabricSpec:
    stitch_pattern: StitchPattern
    border_pattern: Optional[StitchPattern]
    yarn_requirements: YarnSpec
    gauge: Dict[str, float]  # stitches per inch, rows per inch
    construction_notes: List[str]  # cables for structure, lace for drape, etc.


@dataclass
class PatternInstruction:
    step: int
    instruction: str
    stitch_count: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class ConstructionZone:
    name: str  # "border", "main_body", "edging"
    stitch_pattern: StitchPattern
    relative_position: str  # "top", "bottom", "sides", "center"
    priority: int  # construction order


@dataclass
class ConstructionSpec:
    target_dimensions: Dimensions
    construction_zones: List[ConstructionZone]
    construction_sequence: List[
        str
    ]  # ordered steps: ["cast_on", "bottom_border", "main_body", "top_border", "bind_off"]
    finishing_requirements: List[str]  # ["blocking", "seaming", "edge_finishing"]
    structural_notes: List[str]  # construction-specific guidance


@dataclass
class PatternSpec:
    title: str
    instructions: List[PatternInstruction]
    materials: Dict[str, str]
    gauge_info: Dict[str, float]
    finished_dimensions: Dimensions
    estimated_yardage: int  # calculated based on dimensions and gauge
