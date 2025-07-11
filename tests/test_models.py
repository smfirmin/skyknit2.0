import pytest

from src.models.knitting_models import (
    ConstructionSpec,
    ConstructionZone,
    Dimensions,
    FabricSpec,
    PatternInstruction,
    PatternSpec,
    ProjectType,
    RequirementsSpec,
    StitchPattern,
    YarnSpec,
)


class TestProjectType:
    def test_project_type_enum_values(self):
        assert ProjectType.BLANKET.value == "blanket"

    def test_project_type_enum_membership(self):
        assert ProjectType.BLANKET in ProjectType


class TestYarnSpec:
    def test_yarn_spec_creation(self):
        yarn = YarnSpec(weight="worsted", fiber="wool", color="red")
        assert yarn.weight == "worsted"
        assert yarn.fiber == "wool"
        assert yarn.color == "red"

    def test_yarn_spec_optional_color(self):
        yarn = YarnSpec(weight="DK", fiber="cotton")
        assert yarn.weight == "DK"
        assert yarn.fiber == "cotton"
        assert yarn.color is None

    def test_yarn_spec_equality(self):
        yarn1 = YarnSpec(weight="worsted", fiber="wool")
        yarn2 = YarnSpec(weight="worsted", fiber="wool")
        assert yarn1 == yarn2


class TestDimensions:
    def test_dimensions_creation(self):
        dims = Dimensions(width=48.0, length=60.0)
        assert dims.width == 48.0
        assert dims.length == 60.0

    def test_dimensions_equality(self):
        dims1 = Dimensions(width=48.0, length=60.0)
        dims2 = Dimensions(width=48.0, length=60.0)
        assert dims1 == dims2

    def test_dimensions_inequality(self):
        dims1 = Dimensions(width=48.0, length=60.0)
        dims2 = Dimensions(width=50.0, length=60.0)
        assert dims1 != dims2


class TestRequirementsSpec:
    def test_requirements_spec_creation(self):
        dims = Dimensions(width=48.0, length=60.0)
        req = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=dims,
            style_preferences={"texture": "simple"},
            special_requirements=["easy care"],
        )
        assert req.project_type == ProjectType.BLANKET
        assert req.dimensions == dims
        assert req.style_preferences["texture"] == "simple"
        assert "easy care" in req.special_requirements

    def test_requirements_spec_empty_lists(self):
        dims = Dimensions(width=48.0, length=60.0)
        req = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=dims,
            style_preferences={},
            special_requirements=[],
        )
        assert req.style_preferences == {}
        assert req.special_requirements == []


class TestStitchPattern:
    def test_stitch_pattern_creation(self):
        pattern = StitchPattern(
            name="Stockinette",
            row_repeat=2,
            stitch_repeat=1,
            instructions=["Knit", "Purl"],
        )
        assert pattern.name == "Stockinette"
        assert pattern.row_repeat == 2
        assert pattern.stitch_repeat == 1
        assert len(pattern.instructions) == 2

    def test_stitch_pattern_complex(self):
        pattern = StitchPattern(
            name="Simple Cable",
            row_repeat=8,
            stitch_repeat=12,
            instructions=["C6F", "K6", "P6"],
        )
        assert pattern.name == "Simple Cable"
        assert pattern.row_repeat == 8
        assert pattern.stitch_repeat == 12


class TestFabricSpec:
    def test_fabric_spec_creation(self):
        stitch_pattern = StitchPattern("Stockinette", 2, 1, ["K", "P"])
        border_pattern = StitchPattern("Seed Stitch", 2, 2, ["K1, P1", "P1, K1"])
        yarn = YarnSpec("worsted", "wool")

        fabric = FabricSpec(
            stitch_pattern=stitch_pattern,
            border_pattern=border_pattern,
            yarn_requirements=yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=["simple construction"],
        )

        assert fabric.stitch_pattern == stitch_pattern
        assert fabric.border_pattern == border_pattern
        assert fabric.yarn_requirements == yarn
        assert fabric.gauge["stitches_per_inch"] == 4.0
        assert "simple construction" in fabric.construction_notes

    def test_fabric_spec_optional_border(self):
        stitch_pattern = StitchPattern("Stockinette", 2, 1, ["K", "P"])
        yarn = YarnSpec("worsted", "wool")

        fabric = FabricSpec(
            stitch_pattern=stitch_pattern,
            border_pattern=None,
            yarn_requirements=yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=[],
        )

        assert fabric.border_pattern is None


class TestPatternInstruction:
    def test_pattern_instruction_creation(self):
        instruction = PatternInstruction(
            step=1,
            instruction="Cast on 200 stitches",
            stitch_count=200,
            notes="Use long-tail cast on",
        )
        assert instruction.step == 1
        assert instruction.instruction == "Cast on 200 stitches"
        assert instruction.stitch_count == 200
        assert instruction.notes == "Use long-tail cast on"

    def test_pattern_instruction_optional_fields(self):
        instruction = PatternInstruction(
            step=2, instruction="Work in stockinette stitch"
        )
        assert instruction.step == 2
        assert instruction.instruction == "Work in stockinette stitch"
        assert instruction.stitch_count is None
        assert instruction.notes is None


class TestConstructionZone:
    def test_construction_zone_creation(self):
        pattern = StitchPattern("Seed Stitch", 2, 2, ["K1, P1", "P1, K1"])
        zone = ConstructionZone(
            name="border",
            stitch_pattern=pattern,
            relative_position="bottom",
            priority=1,
        )
        assert zone.name == "border"
        assert zone.stitch_pattern == pattern
        assert zone.relative_position == "bottom"
        assert zone.priority == 1


class TestConstructionSpec:
    def test_construction_spec_creation(self):
        dims = Dimensions(width=48.0, length=60.0)
        pattern = StitchPattern("Stockinette", 2, 1, ["K", "P"])
        zone = ConstructionZone("main_body", pattern, "center", 2)

        construction = ConstructionSpec(
            target_dimensions=dims,
            construction_zones=[zone],
            construction_sequence=["cast_on", "main_body", "bind_off"],
            finishing_requirements=["blocking"],
            structural_notes=["work flat"],
        )

        assert construction.target_dimensions == dims
        assert len(construction.construction_zones) == 1
        assert construction.construction_zones[0] == zone
        assert "cast_on" in construction.construction_sequence
        assert "blocking" in construction.finishing_requirements
        assert "work flat" in construction.structural_notes


class TestPatternSpec:
    def test_pattern_spec_creation(self):
        dims = Dimensions(width=48.0, length=60.0)
        instruction = PatternInstruction(1, "Cast on 200 stitches")

        pattern = PatternSpec(
            title="Simple Blanket",
            instructions=[instruction],
            materials={"yarn": "worsted weight wool"},
            gauge_info={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            finished_dimensions=dims,
            estimated_yardage=1000,
        )

        assert pattern.title == "Simple Blanket"
        assert len(pattern.instructions) == 1
        assert pattern.instructions[0] == instruction
        assert pattern.materials["yarn"] == "worsted weight wool"
        assert pattern.gauge_info["stitches_per_inch"] == 4.0
        assert pattern.finished_dimensions == dims
        assert pattern.estimated_yardage == 1000
