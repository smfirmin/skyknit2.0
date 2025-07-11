import pytest

from src.agents.base_agent import AgentType, Message
from src.agents.validation_agent import ValidationAgent
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


class TestValidationAgent:
    def setup_method(self):
        self.agent = ValidationAgent()

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

        self.construction_spec = ConstructionSpec(
            target_dimensions=self.requirements.dimensions,
            construction_zones=[],
            construction_sequence=["cast_on", "main_body", "bind_off"],
            finishing_requirements=["weave_in_ends", "blocking"],
            structural_notes=["work flat"],
        )

        # Typical stitch result that should pass validation
        self.good_stitch_result = {
            "cast_on_stitches": 192,  # 48" * 4 = 192 (no border for math test)
            "total_rows": 330,  # 60" * 5.5 = 330
            "actual_dimensions": {
                "width": 48.0,
                "length": 60.0,
            },  # Matches target exactly
            "stitch_instructions": ["Cast on 192 stitches", "Work in pattern"],
        }

    def test_initialization(self):
        assert self.agent.agent_type == AgentType.VALIDATION
        assert self.agent.tolerance == 0.5

    def test_validate_input_valid(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
            "stitch_result": self.good_stitch_result,
            "requirements": self.requirements,
        }
        assert self.agent.validate_input(input_data) is True

    def test_validate_input_missing_fields(self):
        # Missing fabric_spec
        input_data = {
            "construction_spec": self.construction_spec,
            "stitch_result": self.good_stitch_result,
            "requirements": self.requirements,
        }
        assert self.agent.validate_input(input_data) is False

        # Missing stitch_result
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
            "requirements": self.requirements,
        }
        assert self.agent.validate_input(input_data) is False

    def test_process_valid_pattern(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
            "stitch_result": self.good_stitch_result,
            "requirements": self.requirements,
        }
        result = self.agent.process(input_data)

        assert "validation" in result
        validation = result["validation"]

        assert "is_valid" in validation
        assert "errors" in validation
        assert "warnings" in validation
        assert "suggestions" in validation

        # Should be valid with no errors
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0

    def test_validate_dimension_accuracy_within_tolerance(self):
        actual_dims = {"width": 48.3, "length": 59.7}
        validation = self.agent._validate_dimension_accuracy(
            self.requirements, actual_dims
        )

        assert validation["width_accurate"] is True
        assert validation["length_accurate"] is True
        assert validation["within_tolerance"] is True
        assert validation["width_difference"] == 0.3
        assert validation["length_difference"] == 0.3

    def test_validate_dimension_accuracy_outside_tolerance(self):
        actual_dims = {"width": 49.0, "length": 58.0}  # 1" and 2" off
        validation = self.agent._validate_dimension_accuracy(
            self.requirements, actual_dims
        )

        assert validation["width_accurate"] is False
        assert validation["length_accurate"] is False
        assert validation["within_tolerance"] is False
        assert validation["width_difference"] == 1.0
        assert validation["length_difference"] == 2.0

    def test_validate_stitch_math_correct(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        self.agent._validate_stitch_math(
            self.requirements,
            self.fabric_spec,
            self.good_stitch_result,
            validation_results,
        )

        # Should have no errors
        assert len(validation_results["errors"]) == 0

    def test_validate_stitch_math_width_error(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Bad stitch result with incorrect width calculation
        bad_stitch_result = {
            "cast_on_stitches": 100,  # Way too few stitches
            "total_rows": 330,
            "actual_dimensions": {"width": 25.0, "length": 60.0},
            "stitch_instructions": [],
        }

        self.agent._validate_stitch_math(
            self.requirements, self.fabric_spec, bad_stitch_result, validation_results
        )

        # Should have width error
        assert len(validation_results["errors"]) > 0
        assert any(
            "Width calculation error" in error for error in validation_results["errors"]
        )

    def test_validate_stitch_math_negative_values(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Bad stitch result with negative values
        bad_stitch_result = {
            "cast_on_stitches": -10,
            "total_rows": 0,
            "actual_dimensions": {"width": 48.0, "length": 60.0},
            "stitch_instructions": [],
        }

        self.agent._validate_stitch_math(
            self.requirements, self.fabric_spec, bad_stitch_result, validation_results
        )

        # Should have errors for negative/zero values
        assert len(validation_results["errors"]) >= 2
        assert any(
            "Cast-on stitch count must be positive" in error
            for error in validation_results["errors"]
        )
        assert any(
            "Total row count must be positive" in error
            for error in validation_results["errors"]
        )

    def test_validate_yarn_requirements_good_gauge(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        self.agent._validate_yarn_requirements(
            self.requirements, self.fabric_spec, validation_results
        )

        # Worsted weight with 4.0 sts/inch should be fine
        assert len(validation_results["warnings"]) == 0

    def test_validate_yarn_requirements_unusual_gauge(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Create fabric with unusual gauge for yarn weight
        bad_fabric = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=YarnSpec("worsted", "wool"),
            gauge={
                "stitches_per_inch": 8.0,
                "rows_per_inch": 10.0,
            },  # Too tight for worsted
            construction_notes=[],
        )

        self.agent._validate_yarn_requirements(
            self.requirements, bad_fabric, validation_results
        )

        # Should warn about unusual gauge
        assert len(validation_results["warnings"]) > 0
        assert any(
            "unusual" in warning.lower() for warning in validation_results["warnings"]
        )

    def test_validate_pattern_logic_good_repeat(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Create pattern with good repeat
        cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        cable_fabric = FabricSpec(
            stitch_pattern=cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=[],
        )

        # 200 total stitches - 8 border = 192 pattern stitches, which divides by 12
        stitch_result = {
            "cast_on_stitches": 200,
            "total_rows": 320,  # Divisible by 8
            "actual_dimensions": {"width": 50.0, "length": 53.3},
            "stitch_instructions": [],
        }

        self.agent._validate_pattern_logic(
            cable_fabric, stitch_result, validation_results
        )

        # Should have no errors
        assert len(validation_results["errors"]) == 0

    def test_validate_pattern_logic_bad_stitch_repeat(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Create pattern with problematic repeat
        cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        cable_fabric = FabricSpec(
            stitch_pattern=cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=[],
        )

        # 199 total stitches - 8 border = 191 pattern stitches, which doesn't divide by 12
        stitch_result = {
            "cast_on_stitches": 199,
            "total_rows": 320,
            "actual_dimensions": {"width": 49.75, "length": 53.3},
            "stitch_instructions": [],
        }

        self.agent._validate_pattern_logic(
            cable_fabric, stitch_result, validation_results
        )

        # Should have stitch repeat error
        assert len(validation_results["errors"]) > 0
        assert any(
            "repeat" in error.lower() and "divide" in error.lower()
            for error in validation_results["errors"]
        )

    def test_validate_pattern_logic_row_repeat_suggestion(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Create pattern where rows don't divide evenly
        cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        cable_fabric = FabricSpec(
            stitch_pattern=cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=[],
        )

        stitch_result = {
            "cast_on_stitches": 200,
            "total_rows": 325,  # Not divisible by 8
            "actual_dimensions": {"width": 50.0, "length": 54.2},
            "stitch_instructions": [],
        }

        self.agent._validate_pattern_logic(
            cable_fabric, stitch_result, validation_results
        )

        # Should suggest adjusting for complete pattern
        assert len(validation_results["suggestions"]) > 0
        assert any(
            "complete pattern" in suggestion
            for suggestion in validation_results["suggestions"]
        )

    def test_validate_skill_level_consistency_fingering_warning(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Intermediate pattern with fingering weight
        cable_fabric = FabricSpec(
            stitch_pattern=StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"]),
            border_pattern=self.border_pattern,
            yarn_requirements=YarnSpec("fingering", "wool"),
            gauge={"stitches_per_inch": 7.0, "rows_per_inch": 9.0},
            construction_notes=[],
        )

        self.agent._validate_skill_level_consistency(cable_fabric, validation_results)

        # Should warn about fingering + intermediate pattern
        assert len(validation_results["warnings"]) > 0
        assert any(
            "fingering" in warning.lower() for warning in validation_results["warnings"]
        )

    def test_validate_construction_feasibility_large_project(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Very large project
        large_requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=80.0, length=100.0),  # 8000 sq in
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

        self.agent._validate_construction_feasibility(
            large_requirements, self.fabric_spec, validation_results
        )

        # Should warn about large project
        assert len(validation_results["warnings"]) > 0
        assert any(
            "large project" in warning.lower()
            for warning in validation_results["warnings"]
        )

    def test_validate_construction_feasibility_small_project(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Very small project
        small_requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=5.0, length=8.0),  # 40 sq in
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

        self.agent._validate_construction_feasibility(
            small_requirements, self.fabric_spec, validation_results
        )

        # Should warn about small project
        assert len(validation_results["warnings"]) > 0
        assert any(
            "small project" in warning.lower()
            for warning in validation_results["warnings"]
        )

    def test_validate_construction_feasibility_extreme_gauge(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Very tight gauge
        tight_fabric = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 10.0, "rows_per_inch": 12.0},
            construction_notes=[],
        )

        self.agent._validate_construction_feasibility(
            self.requirements, tight_fabric, validation_results
        )

        # Should suggest about tight gauge
        assert len(validation_results["suggestions"]) > 0
        assert any(
            "tight gauge" in suggestion.lower()
            for suggestion in validation_results["suggestions"]
        )

    def test_validate_construction_feasibility_loose_gauge(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Very loose gauge
        loose_fabric = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 1.5, "rows_per_inch": 2.0},
            construction_notes=[],
        )

        self.agent._validate_construction_feasibility(
            self.requirements, loose_fabric, validation_results
        )

        # Should suggest about loose gauge
        assert len(validation_results["suggestions"]) > 0
        assert any(
            "loose gauge" in suggestion.lower()
            for suggestion in validation_results["suggestions"]
        )

    def test_validate_construction_feasibility_blocking_chunky(self):
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Chunky yarn with blocking notes
        chunky_fabric = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=YarnSpec("chunky", "wool"),
            gauge={"stitches_per_inch": 3.0, "rows_per_inch": 4.0},
            construction_notes=["Block finished piece to even out tension"],
        )

        self.agent._validate_construction_feasibility(
            self.requirements, chunky_fabric, validation_results
        )

        # Should suggest about blocking chunky yarn
        assert len(validation_results["suggestions"]) > 0
        assert any(
            "blocking" in suggestion.lower() and "chunky" in suggestion.lower()
            for suggestion in validation_results["suggestions"]
        )

    def test_handle_message(self):
        message = Message(
            sender=AgentType.STITCH,
            recipient=AgentType.VALIDATION,
            content={"test": "data"},
            message_type="test",
        )
        result = self.agent.handle_message(message)
        assert result["status"] == "acknowledged"

    def test_process_adds_dimension_validation_to_stitch_result(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
            "stitch_result": self.good_stitch_result.copy(),
            "requirements": self.requirements,
        }

        self.agent.process(input_data)

        # Check that dimension_validation was added to stitch_result
        assert "dimension_validation" in input_data["stitch_result"]
        dim_validation = input_data["stitch_result"]["dimension_validation"]
        assert "width_accurate" in dim_validation
        assert "length_accurate" in dim_validation
        assert "within_tolerance" in dim_validation
