import pytest

from src.agents.base_agent import AgentType, Message
from src.agents.stitch_agent import StitchAgent
from src.models.knitting_models import (
    ConstructionSpec,
    ConstructionZone,
    Dimensions,
    FabricSpec,
    ProjectType,
    RequirementsSpec,
    StitchPattern,
    YarnSpec,
)


class TestStitchAgent:
    def setup_method(self):
        self.agent = StitchAgent()

        # Create common test data
        self.dimensions = Dimensions(width=48.0, length=60.0)

        self.stockinette_pattern = StitchPattern("Stockinette", 2, 1, ["K", "P"])
        self.cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        self.border_pattern = StitchPattern(
            "Seed Stitch Border", 2, 2, ["K1, P1", "P1, K1"]
        )

        self.yarn = YarnSpec("worsted", "wool")

        self.fabric_spec = FabricSpec(
            stitch_pattern=self.stockinette_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=["simple construction"],
        )

        # Construction zones with border
        self.border_zone = ConstructionZone(
            name="border",
            stitch_pattern=self.border_pattern,
            relative_position="perimeter",
            priority=1,
        )

        self.main_zone = ConstructionZone(
            name="main_body",
            stitch_pattern=self.stockinette_pattern,
            relative_position="center",
            priority=2,
        )

        self.construction_spec = ConstructionSpec(
            target_dimensions=self.dimensions,
            construction_zones=[self.border_zone, self.main_zone],
            construction_sequence=[
                "cast_on",
                "bottom_border",
                "main_body_with_side_borders",
                "top_border",
                "bind_off",
                "finishing",
            ],
            finishing_requirements=["weave_in_ends", "blocking"],
            structural_notes=["work flat"],
        )

    def test_initialization(self):
        assert self.agent.agent_type == AgentType.STITCH

    def test_validate_input_valid(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
        }
        assert self.agent.validate_input(input_data) is True

    def test_validate_input_missing_fabric_spec(self):
        input_data = {"construction_spec": self.construction_spec}
        assert self.agent.validate_input(input_data) is False

    def test_validate_input_missing_construction_spec(self):
        input_data = {"fabric_spec": self.fabric_spec}
        assert self.agent.validate_input(input_data) is False

    def test_validate_input_missing_gauge(self):
        bad_fabric = type("MockFabric", (), {})()
        input_data = {
            "fabric_spec": bad_fabric,
            "construction_spec": self.construction_spec,
        }
        assert self.agent.validate_input(input_data) is False

    def test_validate_input_missing_target_dimensions(self):
        bad_construction = type("MockConstruction", (), {})()
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": bad_construction,
        }
        assert self.agent.validate_input(input_data) is False

    def test_process_complete(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
        }
        result = self.agent.process(input_data)

        # Check all expected outputs
        assert "stitch_instructions" in result
        assert "cast_on_stitches" in result
        assert "total_rows" in result
        assert "actual_dimensions" in result

        # Check types
        assert isinstance(result["stitch_instructions"], list)
        assert isinstance(result["cast_on_stitches"], int)
        assert isinstance(result["total_rows"], int)
        assert isinstance(result["actual_dimensions"], dict)

        # Check basic values
        assert result["cast_on_stitches"] > 0
        assert result["total_rows"] > 0
        assert len(result["stitch_instructions"]) > 0

    def test_calculate_cast_on_stitches_with_border(self):
        cast_on = self.agent._calculate_cast_on_stitches(
            self.fabric_spec, self.construction_spec
        )

        # 48" * 4 sts/inch = 192 + 8 border stitches = 200
        expected = 48 * 4 + 8  # target width * gauge + border
        assert cast_on == expected

    def test_calculate_cast_on_stitches_without_border(self):
        # Construction without border
        no_border_construction = ConstructionSpec(
            target_dimensions=self.dimensions,
            construction_zones=[self.main_zone],
            construction_sequence=["cast_on", "main_body", "bind_off"],
            finishing_requirements=["weave_in_ends", "blocking"],
            structural_notes=["work flat"],
        )

        cast_on = self.agent._calculate_cast_on_stitches(
            self.fabric_spec, no_border_construction
        )

        # 48" * 4 sts/inch = 192, no border
        expected = 48 * 4
        assert cast_on == expected

    def test_calculate_cast_on_stitches_with_pattern_repeat(self):
        # Create cable fabric spec
        cable_fabric = FabricSpec(
            stitch_pattern=self.cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=["cable construction"],
        )

        # Update main zone to use cable pattern
        cable_main_zone = ConstructionZone(
            name="main_body",
            stitch_pattern=self.cable_pattern,
            relative_position="center",
            priority=2,
        )

        cable_construction = ConstructionSpec(
            target_dimensions=self.dimensions,
            construction_zones=[self.border_zone, cable_main_zone],
            construction_sequence=[
                "cast_on",
                "bottom_border",
                "main_body_with_side_borders",
                "top_border",
                "bind_off",
            ],
            finishing_requirements=["weave_in_ends", "blocking"],
            structural_notes=["work flat"],
        )

        cast_on = self.agent._calculate_cast_on_stitches(
            cable_fabric, cable_construction
        )

        # 48" * 4 = 192, rounded to nearest 12 (pattern repeat) = 192, + 8 border = 200
        base_stitches = 48 * 4  # 192
        pattern_repeat = 12
        adjusted_pattern = (
            (base_stitches + pattern_repeat - 1) // pattern_repeat
        ) * pattern_repeat  # 192
        expected = adjusted_pattern + 8  # + border
        assert cast_on == expected

    def test_calculate_total_rows(self):
        total_rows = self.agent._calculate_total_rows(
            self.fabric_spec, self.construction_spec
        )

        # 60" * 5.5 rows/inch = 330, adjusted to nearest 2 (row repeat) = 330
        expected = int(60 * 5.5)
        # Should be adjusted to multiple of row repeat (2)
        row_repeat = 2
        expected = ((expected + row_repeat - 1) // row_repeat) * row_repeat
        assert total_rows == expected

    def test_calculate_total_rows_with_pattern_repeat(self):
        # Use cable pattern with 8-row repeat
        cable_fabric = FabricSpec(
            stitch_pattern=self.cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=["cable construction"],
        )

        cable_main_zone = ConstructionZone(
            name="main_body",
            stitch_pattern=self.cable_pattern,
            relative_position="center",
            priority=2,
        )

        cable_construction = ConstructionSpec(
            target_dimensions=self.dimensions,
            construction_zones=[self.border_zone, cable_main_zone],
            construction_sequence=["cast_on", "main_body", "bind_off"],
            finishing_requirements=["weave_in_ends", "blocking"],
            structural_notes=["work flat"],
        )

        total_rows = self.agent._calculate_total_rows(cable_fabric, cable_construction)

        # 60" * 6 = 360, adjusted to nearest 8 (row repeat) = 360
        base_rows = int(60 * 6)  # 360
        row_repeat = 8
        expected = ((base_rows + row_repeat - 1) // row_repeat) * row_repeat
        assert total_rows == expected

    def test_calculate_actual_dimensions(self):
        cast_on_stitches = 200
        total_rows = 330

        actual_dims = self.agent._calculate_actual_dimensions(
            self.fabric_spec, cast_on_stitches, total_rows
        )

        expected_width = 200 / 4.0  # 50.0
        expected_length = 330 / 5.5  # 60.0

        assert actual_dims["width"] == round(expected_width, 2)
        assert actual_dims["length"] == round(expected_length, 2)

    def test_generate_stitch_instructions_basic_structure(self):
        instructions = self.agent._generate_stitch_instructions(
            self.construction_spec, self.fabric_spec, 200
        )

        # Should start with cast on
        assert instructions[0].startswith("Cast on")
        assert "200" in instructions[0]

        # Should contain pattern instructions
        instruction_text = " ".join(instructions)
        assert "Border Row" in instruction_text
        assert "Stockinette" in instruction_text
        assert "Bind off" in instruction_text

    def test_generate_stitch_instructions_without_border(self):
        no_border_construction = ConstructionSpec(
            target_dimensions=self.dimensions,
            construction_zones=[self.main_zone],
            construction_sequence=["cast_on", "main_body", "bind_off", "finishing"],
            finishing_requirements=["weave_in_ends", "blocking"],
            structural_notes=["work flat"],
        )

        instructions = self.agent._generate_stitch_instructions(
            no_border_construction, self.fabric_spec, 192
        )

        instruction_text = " ".join(instructions)
        assert "Border Row" not in instruction_text
        assert "Stockinette" in instruction_text
        assert "Bind off" in instruction_text

    def test_generate_border_instructions(self):
        instructions = self.agent._generate_border_instructions(self.border_pattern)

        assert len(instructions) >= 3  # Row instructions + repeat instruction
        assert "Border Row 1:" in instructions[0]
        assert "Border Row 2:" in instructions[1]
        assert "Repeat border rows" in instructions[-1]

    def test_generate_main_pattern_instructions(self):
        instructions = self.agent._generate_main_pattern_instructions(
            self.stockinette_pattern
        )

        assert len(instructions) >= 4  # Pattern setup + row instructions + repeat
        assert "Begin Stockinette pattern:" in instructions[0]
        assert "Row 1:" in instructions[1]
        assert "Row 2:" in instructions[2]
        assert "Repeat rows" in instructions[-1]

    def test_generate_finishing_instructions_basic(self):
        finishing_reqs = ["weave_in_ends", "blocking"]
        instructions = self.agent._generate_finishing_instructions(finishing_reqs)

        assert len(instructions) == 2
        assert "Weave in all loose ends" in instructions[0]
        assert "Block piece to measurements" in instructions[1]

    def test_generate_finishing_instructions_cable(self):
        finishing_reqs = ["weave_in_ends", "blocking", "cable_blocking"]
        instructions = self.agent._generate_finishing_instructions(finishing_reqs)

        assert len(instructions) == 3
        assert any("cable definition" in inst for inst in instructions)

    def test_generate_finishing_instructions_lace(self):
        finishing_reqs = ["weave_in_ends", "blocking", "aggressive_blocking"]
        instructions = self.agent._generate_finishing_instructions(finishing_reqs)

        assert len(instructions) == 3
        assert any("aggressively" in inst for inst in instructions)
        assert any("lace pattern" in inst for inst in instructions)

    def test_handle_message(self):
        message = Message(
            sender=AgentType.CONSTRUCTION,
            recipient=AgentType.STITCH,
            content={"test": "data"},
            message_type="test",
        )
        result = self.agent.handle_message(message)
        assert result["status"] == "acknowledged"

    def test_pattern_repeat_edge_cases(self):
        # Test when target stitches is already a multiple of pattern repeat
        # 48" * 4 = 192, which is exactly divisible by 12
        cable_fabric = FabricSpec(
            stitch_pattern=self.cable_pattern,
            border_pattern=None,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=["cable construction"],
        )

        cable_main_zone = ConstructionZone(
            name="main_body",
            stitch_pattern=self.cable_pattern,
            relative_position="center",
            priority=2,
        )

        cable_construction = ConstructionSpec(
            target_dimensions=self.dimensions,
            construction_zones=[cable_main_zone],
            construction_sequence=["cast_on", "main_body", "bind_off"],
            finishing_requirements=["weave_in_ends"],
            structural_notes=["work flat"],
        )

        cast_on = self.agent._calculate_cast_on_stitches(
            cable_fabric, cable_construction
        )

        # 192 is already divisible by 12, so should remain 192
        assert cast_on == 192
        assert cast_on % 12 == 0
