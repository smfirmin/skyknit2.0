import pytest

from src.agents.base_agent import AgentType, Message
from src.agents.construction_agent import ConstructionAgent
from src.exceptions import ConstructionPlanningError, ValidationError
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


class TestConstructionAgent:
    def setup_method(self):
        self.agent = ConstructionAgent()

        # Create common test data
        self.requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

        self.stitch_pattern = StitchPattern("Stockinette", 2, 1, ["K", "P"])
        self.border_pattern = StitchPattern(
            "Seed Stitch Border", 2, 2, ["K1, P1", "P1, K1"]
        )
        self.yarn = YarnSpec("worsted", "wool")

        self.fabric_spec = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=["simple construction"],
        )

    def test_initialization(self):
        assert self.agent.agent_type == AgentType.CONSTRUCTION

    def test_validate_input_valid(self):
        input_data = {
            "requirements": self.requirements,
            "fabric_spec": self.fabric_spec,
        }
        assert self.agent.validate_input(input_data) is True

    def test_validate_input_missing_requirements(self):
        input_data = {"fabric_spec": self.fabric_spec}
        assert self.agent.validate_input(input_data) is False

    def test_validate_input_missing_fabric_spec(self):
        input_data = {"requirements": self.requirements}
        assert self.agent.validate_input(input_data) is False

    def test_validate_input_missing_dimensions(self):
        # Create requirements without dimensions
        bad_requirements = type("MockReq", (), {})()
        input_data = {"requirements": bad_requirements, "fabric_spec": self.fabric_spec}
        assert self.agent.validate_input(input_data) is False

    def test_process_blanket_with_border(self):
        input_data = {
            "requirements": self.requirements,
            "fabric_spec": self.fabric_spec,
        }
        result = self.agent.process(input_data)

        assert "construction_spec" in result
        construction_spec = result["construction_spec"]

        assert isinstance(construction_spec, ConstructionSpec)
        assert construction_spec.target_dimensions == self.requirements.dimensions
        assert len(construction_spec.construction_zones) == 2  # border + main body
        assert len(construction_spec.construction_sequence) > 0
        assert len(construction_spec.finishing_requirements) > 0
        assert len(construction_spec.structural_notes) > 0

    def test_process_blanket_without_border(self):
        # Create fabric spec without border
        fabric_no_border = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=None,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=["simple construction"],
        )

        input_data = {
            "requirements": self.requirements,
            "fabric_spec": fabric_no_border,
        }
        result = self.agent.process(input_data)

        construction_spec = result["construction_spec"]
        assert len(construction_spec.construction_zones) == 1  # main body only

        # Check sequence doesn't include border steps
        sequence = construction_spec.construction_sequence
        assert "bottom_border" not in sequence
        assert "top_border" not in sequence
        assert "main_body" in sequence

    def test_plan_construction_zones_with_border(self):
        zones = self.agent._plan_construction_zones(self.requirements, self.fabric_spec)

        assert len(zones) == 2

        # Check border zone
        border_zone = next(z for z in zones if z.name == "border")
        assert border_zone.stitch_pattern == self.border_pattern
        assert border_zone.relative_position == "perimeter"
        assert border_zone.priority == 1

        # Check main body zone
        main_zone = next(z for z in zones if z.name == "main_body")
        assert main_zone.stitch_pattern == self.stitch_pattern
        assert main_zone.relative_position == "center"
        assert main_zone.priority == 2

    def test_plan_construction_zones_without_border(self):
        fabric_no_border = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=None,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=[],
        )

        zones = self.agent._plan_construction_zones(self.requirements, fabric_no_border)

        assert len(zones) == 1
        assert zones[0].name == "main_body"

    def test_plan_construction_sequence_with_border(self):
        zones = self.agent._plan_construction_zones(self.requirements, self.fabric_spec)
        sequence = self.agent._plan_construction_sequence(self.requirements, zones)

        assert "cast_on" in sequence
        assert "bottom_border" in sequence
        assert "main_body_with_side_borders" in sequence
        assert "top_border" in sequence
        assert "bind_off" in sequence
        assert "finishing" in sequence

        # Check order
        assert sequence.index("cast_on") < sequence.index("bottom_border")
        assert sequence.index("bottom_border") < sequence.index(
            "main_body_with_side_borders"
        )
        assert sequence.index("main_body_with_side_borders") < sequence.index(
            "top_border"
        )
        assert sequence.index("top_border") < sequence.index("bind_off")

    def test_plan_construction_sequence_without_border(self):
        fabric_no_border = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=None,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=[],
        )
        zones = self.agent._plan_construction_zones(self.requirements, fabric_no_border)
        sequence = self.agent._plan_construction_sequence(self.requirements, zones)

        assert "cast_on" in sequence
        assert "main_body" in sequence
        assert "bind_off" in sequence
        assert "finishing" in sequence
        assert "bottom_border" not in sequence
        assert "top_border" not in sequence

    def test_plan_finishing_requirements_basic(self):
        finishing = self.agent._plan_finishing_requirements(
            self.requirements, self.fabric_spec
        )

        assert "weave_in_ends" in finishing
        assert "blocking" in finishing

    def test_plan_finishing_requirements_cable(self):
        cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        cable_fabric = FabricSpec(
            stitch_pattern=cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=["cable construction"],
        )

        finishing = self.agent._plan_finishing_requirements(
            self.requirements, cable_fabric
        )

        assert "weave_in_ends" in finishing
        assert "blocking" in finishing
        assert "cable_blocking" in finishing

    def test_plan_finishing_requirements_lace(self):
        lace_pattern = StitchPattern("Simple Lace", 4, 8, ["YO", "K2tog"])
        lace_fabric = FabricSpec(
            stitch_pattern=lace_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 3.5, "rows_per_inch": 5.0},
            construction_notes=["lace construction"],
        )

        finishing = self.agent._plan_finishing_requirements(
            self.requirements, lace_fabric
        )

        assert "weave_in_ends" in finishing
        assert "blocking" in finishing
        assert "aggressive_blocking" in finishing

    def test_generate_structural_notes_small_project(self):
        small_requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=30.0, length=40.0),  # 1200 sq in
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

        zones = self.agent._plan_construction_zones(
            small_requirements, self.fabric_spec
        )
        notes = self.agent._generate_structural_notes(
            small_requirements, self.fabric_spec, zones
        )

        assert isinstance(notes, list)
        assert len(notes) > 0

        # Should not have large project warnings
        assert not any("Large project" in note for note in notes)
        assert not any("heavy" in note for note in notes)

    def test_generate_structural_notes_large_project(self):
        large_requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=60.0, length=80.0),  # 4800 sq in
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

        zones = self.agent._plan_construction_zones(
            large_requirements, self.fabric_spec
        )
        notes = self.agent._generate_structural_notes(
            large_requirements, self.fabric_spec, zones
        )

        # Should have large project warnings
        assert any("Large project" in note for note in notes)
        assert any("heavy" in note for note in notes)

    def test_generate_structural_notes_cable_pattern(self):
        cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        cable_fabric = FabricSpec(
            stitch_pattern=cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=["cable construction"],
        )

        zones = self.agent._plan_construction_zones(self.requirements, cable_fabric)
        notes = self.agent._generate_structural_notes(
            self.requirements, cable_fabric, zones
        )

        # Should have cable-specific notes
        assert any("Cable pattern" in note for note in notes)
        assert any("cable needle" in note for note in notes)

    def test_generate_structural_notes_with_border(self):
        zones = self.agent._plan_construction_zones(self.requirements, self.fabric_spec)
        notes = self.agent._generate_structural_notes(
            self.requirements, self.fabric_spec, zones
        )

        # Should have border-specific notes
        assert any("Border integrated" in note for note in notes)
        assert any("edge tension" in note for note in notes)

    def test_generate_structural_notes_general(self):
        zones = self.agent._plan_construction_zones(self.requirements, self.fabric_spec)
        notes = self.agent._generate_structural_notes(
            self.requirements, self.fabric_spec, zones
        )

        # Should have general construction notes
        assert any("worked flat" in note for note in notes)
        assert any("odd-numbered" in note for note in notes)

    def test_handle_message(self):
        message = Message(
            sender=AgentType.FABRIC,
            recipient=AgentType.CONSTRUCTION,
            content={"test": "data"},
            message_type="test",
        )
        result = self.agent.handle_message(message)
        assert result["status"] == "acknowledged"

    def test_process_invalid_input_validation_error(self):
        """Test that invalid input raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"invalid": "data"})

        assert "Invalid input data for construction planning" in str(exc_info.value)
        assert exc_info.value.field == "requirements or fabric_spec"

    def test_validate_construction_inputs_missing_requirements(self):
        """Test validation error when requirements is None"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent._validate_construction_inputs(None, self.fabric_spec)

        assert "Missing requirements for construction planning" in str(exc_info.value)
        assert exc_info.value.field == "requirements"

    def test_validate_construction_inputs_missing_fabric_spec(self):
        """Test validation error when fabric_spec is None"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent._validate_construction_inputs(self.requirements, None)

        assert "Missing fabric specification for construction planning" in str(
            exc_info.value
        )
        assert exc_info.value.field == "fabric_spec"

    def test_validate_construction_inputs_missing_dimensions(self):
        """Test validation error when dimensions is missing"""
        bad_requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=None,  # Missing dimensions
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

        with pytest.raises(ValidationError) as exc_info:
            self.agent._validate_construction_inputs(bad_requirements, self.fabric_spec)

        assert "Missing dimensions in requirements" in str(exc_info.value)
        assert exc_info.value.field == "requirements.dimensions"

    def test_plan_construction_zones_unsupported_project_type(self):
        """Test error handling for unsupported project types"""
        # Create a requirements spec with invalid project type
        from unittest.mock import Mock

        bad_requirements = Mock()
        bad_requirements.project_type = "INVALID_TYPE"

        with pytest.raises(ConstructionPlanningError) as exc_info:
            self.agent._plan_construction_zones(bad_requirements, self.fabric_spec)

        assert "Unsupported project type" in str(exc_info.value)
        assert exc_info.value.construction_type == "project_type_validation"

    def test_plan_construction_zones_missing_stitch_pattern(self):
        """Test error handling when main stitch pattern is missing"""
        bad_fabric = FabricSpec(
            stitch_pattern=None,  # Missing main pattern
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=["test construction"],
        )

        with pytest.raises(ConstructionPlanningError) as exc_info:
            self.agent._plan_construction_zones(self.requirements, bad_fabric)

        assert "Cannot plan construction: missing main stitch pattern" in str(
            exc_info.value
        )
        assert exc_info.value.construction_type == "zone_planning"

    def test_validate_construction_plan_empty_zones(self):
        """Test validation error when no construction zones are provided"""
        with pytest.raises(ConstructionPlanningError) as exc_info:
            self.agent._validate_construction_plan([], ["cast_on"], ["weave_in_ends"])

        assert "No construction zones planned" in str(exc_info.value)
        assert exc_info.value.construction_type == "plan_validation"

    def test_validate_construction_plan_empty_sequence(self):
        """Test validation error when no construction sequence is provided"""
        zones = [self.construction_zone]

        with pytest.raises(ConstructionPlanningError) as exc_info:
            self.agent._validate_construction_plan(zones, [], ["weave_in_ends"])

        assert "No construction sequence planned" in str(exc_info.value)
        assert exc_info.value.construction_type == "plan_validation"

    def test_validate_construction_plan_zone_missing_name(self):
        """Test validation error when construction zone is missing name"""
        from unittest.mock import Mock

        bad_zone = Mock()
        bad_zone.name = None
        bad_zone.stitch_pattern = self.stitch_pattern

        with pytest.raises(ConstructionPlanningError) as exc_info:
            self.agent._validate_construction_plan(
                [bad_zone], ["cast_on"], ["weave_in_ends"]
            )

        assert "Construction zone missing name" in str(exc_info.value)
        assert exc_info.value.construction_type == "zone_validation"
