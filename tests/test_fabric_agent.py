import pytest

from src.agents.base_agent import AgentType, Message
from src.agents.fabric_agent import FabricAgent
from src.models.knitting_models import (
    Dimensions,
    FabricSpec,
    ProjectType,
    RequirementsSpec,
    StitchPattern,
    YarnSpec,
)


class TestFabricAgent:
    def setup_method(self):
        self.agent = FabricAgent()

    def test_initialization(self):
        assert self.agent.agent_type == AgentType.FABRIC

    def test_validate_input_valid(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )
        valid_input = {"requirements": requirements}
        assert self.agent.validate_input(valid_input) is True

    def test_validate_input_missing_requirements(self):
        invalid_input = {"other_key": "value"}
        assert self.agent.validate_input(invalid_input) is False

    def test_validate_input_wrong_type(self):
        invalid_input = {"requirements": "not a RequirementsSpec"}
        # Should now properly fail validation
        assert self.agent.validate_input(invalid_input) is False

    def test_process_simple_blanket(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )
        input_data = {"requirements": requirements}
        result = self.agent.process(input_data)

        assert "fabric_spec" in result
        fabric_spec = result["fabric_spec"]

        assert isinstance(fabric_spec, FabricSpec)
        assert fabric_spec.stitch_pattern.name == "Stockinette"
        assert fabric_spec.yarn_requirements.weight == "worsted"
        assert fabric_spec.yarn_requirements.fiber == "wool"
        assert fabric_spec.border_pattern.name == "Seed Stitch Border"
        assert fabric_spec.gauge["stitches_per_inch"] == 4.0
        assert fabric_spec.gauge["rows_per_inch"] == 5.5

    def test_process_cable_blanket(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "cable"},
            special_requirements=[],
        )
        input_data = {"requirements": requirements}
        result = self.agent.process(input_data)

        fabric_spec = result["fabric_spec"]
        assert fabric_spec.stitch_pattern.name == "Simple Cable"
        assert fabric_spec.stitch_pattern.row_repeat == 8
        assert fabric_spec.stitch_pattern.stitch_repeat == 12
        assert fabric_spec.border_pattern.name == "Seed Stitch Border"

    def test_process_lace_blanket(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "lace"},
            special_requirements=[],
        )
        input_data = {"requirements": requirements}
        result = self.agent.process(input_data)

        fabric_spec = result["fabric_spec"]
        assert fabric_spec.stitch_pattern.name == "Simple Lace"
        assert fabric_spec.stitch_pattern.row_repeat == 4
        assert fabric_spec.stitch_pattern.stitch_repeat == 8

    def test_select_stitch_pattern_simple(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )
        pattern = self.agent._select_stitch_pattern(requirements)

        assert isinstance(pattern, StitchPattern)
        assert pattern.name == "Stockinette"
        assert pattern.row_repeat == 2
        assert pattern.stitch_repeat == 1

    def test_select_stitch_pattern_cable(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "cable"},
            special_requirements=[],
        )
        pattern = self.agent._select_stitch_pattern(requirements)

        assert pattern.name == "Simple Cable"
        assert pattern.row_repeat == 8
        assert pattern.stitch_repeat == 12

    def test_select_yarn_requirements(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )
        yarn = self.agent._determine_yarn_requirements(requirements)

        assert isinstance(yarn, YarnSpec)
        assert yarn.weight == "worsted"
        assert yarn.fiber == "wool"
        assert yarn.color == "natural"

    def test_calculate_gauge_worsted(self):
        gauge = self.agent._calculate_gauge("worsted")

        assert gauge["stitches_per_inch"] == 4.0
        assert gauge["rows_per_inch"] == 5.5

    def test_calculate_gauge_dk(self):
        gauge = self.agent._calculate_gauge("dk")

        assert gauge["stitches_per_inch"] == 5.0
        assert gauge["rows_per_inch"] == 6.0

    def test_calculate_gauge_default(self):
        from src.exceptions import GaugeError

        # Should raise GaugeError for unknown yarn weight
        with pytest.raises(GaugeError) as exc_info:
            self.agent._calculate_gauge("unknown")

        assert "Unsupported yarn weight" in str(exc_info.value)
        assert exc_info.value.yarn_weight == "unknown"

    def test_select_border_pattern_blanket(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )
        border = self.agent._select_border_pattern(requirements)

        assert border is not None
        assert border.name == "Seed Stitch Border"
        assert border.row_repeat == 2
        assert border.stitch_repeat == 2

    def test_create_construction_notes_simple(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )
        pattern = StitchPattern("Stockinette", 2, 1, ["K", "P"])
        notes = self.agent._create_construction_notes(requirements, pattern)

        assert isinstance(notes, list)
        assert len(notes) > 0
        assert any("stockinette" in note.lower() for note in notes)

    def test_create_construction_notes_cable(self):
        requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "cable"},
            special_requirements=[],
        )
        pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        notes = self.agent._create_construction_notes(requirements, pattern)

        assert any("cable" in note.lower() for note in notes)

    def test_handle_message(self):
        message = Message(
            sender=AgentType.REQUIREMENTS,
            recipient=AgentType.FABRIC,
            content={"test": "data"},
            message_type="test",
        )
        result = self.agent.handle_message(message)
        assert result["status"] == "acknowledged"
