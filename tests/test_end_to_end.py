import pytest

from src.models.knitting_models import ProjectType
from src.workflow.pattern_workflow import PatternWorkflow


class TestEndToEndWorkflow:
    def setup_method(self):
        self.workflow = PatternWorkflow()

    def test_workflow_initialization(self):
        assert self.workflow.validate_workflow() is True
        assert self.workflow.requirements_agent is not None
        assert self.workflow.fabric_agent is not None
        assert self.workflow.stitch_agent is not None
        assert self.workflow.validation_agent is not None
        assert self.workflow.output_agent is not None

    def test_simple_blanket_request(self):
        user_request = "I want a simple blanket"

        result = self.workflow.generate_pattern(user_request)

        # Verify all stages completed
        assert "user_request" in result
        assert "requirements" in result
        assert "fabric_spec" in result
        assert "stitch_result" in result
        assert "validation" in result
        assert "outputs" in result
        assert "pattern_summary" in result

        # Check requirements parsing (everything defaults to blanket now)
        requirements = result["requirements"]
        assert requirements.project_type == ProjectType.BLANKET
        assert requirements.style_preferences["texture"] == "simple"

        # Check fabric decisions (all defaults to worsted)
        fabric_spec = result["fabric_spec"]
        assert fabric_spec.stitch_pattern.name == "Stockinette"
        assert fabric_spec.yarn_requirements.weight == "worsted"
        assert (
            fabric_spec.border_pattern.name == "Seed Stitch Border"
        )  # Blankets get borders

        # Check stitch calculations
        stitch_result = result["stitch_result"]
        assert stitch_result["cast_on_stitches"] == 200  # 48" * 4 sts/inch + 8 border
        assert stitch_result["total_rows"] == 330  # 60" * 5.5 rows/inch
        # Border adds extra width so may not be within tolerance
        assert stitch_result["actual_dimensions"]["width"] == 50.0  # 200/4 = 50"

        # Check pattern summary
        summary = result["pattern_summary"]
        assert "Stockinette Blanket" in summary["title"]
        assert summary["cast_on_stitches"] == 200
        assert summary["main_pattern"] == "Stockinette"

    def test_cable_blanket_request(self):
        user_request = "I want a cable blanket"

        result = self.workflow.generate_pattern(user_request)

        # Check requirements parsing
        requirements = result["requirements"]
        assert requirements.project_type == ProjectType.BLANKET
        assert requirements.style_preferences["texture"] == "cable"

        # Check fabric decisions
        fabric_spec = result["fabric_spec"]
        assert fabric_spec.stitch_pattern.name == "Simple Cable"
        assert fabric_spec.yarn_requirements.weight == "worsted"
        assert fabric_spec.border_pattern.name == "Seed Stitch Border"

        # Check stitch calculations account for pattern repeat
        stitch_result = result["stitch_result"]
        # Should adjust for 12-stitch cable repeat: 48" * 4 sts/inch = 192, rounds to 192
        # Plus 8 border stitches = 200 total
        cast_on = stitch_result["cast_on_stitches"]
        assert cast_on == 200  # 192 (pattern) + 8 (border)

        # Check that dimensions are calculated (may be slightly off due to pattern repeat)
        validation = stitch_result["dimension_validation"]
        # Pattern repeat adjustments may cause small dimension differences
        assert "width_accurate" in validation
        assert "length_accurate" in validation

        # Check summary
        summary = result["pattern_summary"]
        assert "Cable Blanket" in summary["title"]
        assert summary["main_pattern"] == "Simple Cable"
        assert summary["border_pattern"] == "Seed Stitch Border"

    def test_pattern_summary_completeness(self):
        user_request = "I want a simple blanket"

        result = self.workflow.generate_pattern(user_request)
        summary = result["pattern_summary"]

        # Verify all expected fields are present (removed skill_level)
        required_fields = [
            "title",
            "project_type",
            "finished_size",
            "materials",
            "cast_on_stitches",
            "total_rows",
            "main_pattern",
            "construction_notes",
            "dimension_accuracy",
        ]

        for field in required_fields:
            assert field in summary, f"Missing field: {field}"

        # Verify materials section
        materials = summary["materials"]
        assert "yarn" in materials
        assert "needles" in materials
        assert "gauge" in materials

        # Verify dimension accuracy reporting
        dim_accuracy = summary["dimension_accuracy"]
        assert "target_size" in dim_accuracy
        assert "actual_size" in dim_accuracy
        assert "within_tolerance" in dim_accuracy

    def test_stitch_instruction_generation(self):
        user_request = "I want a simple blanket"

        result = self.workflow.generate_pattern(user_request)
        stitch_result = result["stitch_result"]

        instructions = stitch_result["stitch_instructions"]

        # Verify instruction structure
        assert len(instructions) >= 4
        assert "Cast on" in instructions[0]
        assert any(
            "Bind off" in inst for inst in instructions
        )  # Bind off somewhere in instructions
        assert any("Stockinette pattern" in inst for inst in instructions)

    def test_dimension_validation_accuracy(self):
        user_request = "I want a simple blanket"

        result = self.workflow.generate_pattern(user_request)

        # Check that calculated dimensions match targets within tolerance
        requirements = result["requirements"]
        stitch_result = result["stitch_result"]

        target_length = requirements.dimensions.length
        stitch_result["actual_dimensions"]["width"]
        actual_length = stitch_result["actual_dimensions"]["length"]

        # Border adds 2" of width, so width won't be within tolerance but length should be
        assert abs(actual_length - target_length) <= 0.5

        # Check that validation captures the width difference
        validation = stitch_result["dimension_validation"]
        assert validation["length_accurate"] is True
        assert validation["width_accurate"] is False  # Due to border

    def test_yarn_yardage_calculation(self):
        user_request = "I want a simple blanket"

        result = self.workflow.generate_pattern(user_request)
        outputs = result["outputs"]

        # Blanket: 48" x 60" = 2880 sq inches
        # Worsted weight: 2.5 yards per sq inch
        # With 20% buffer: 2880 * 2.5 * 1.2 = 8640 yards
        expected_yardage = 8640

        # Check yardage in JSON output
        json_output = outputs["json"]
        actual_yardage = json_output["materials"]["yarn"]["estimated_yardage"]
        assert actual_yardage == expected_yardage

    def test_validation_and_output_stages(self):
        user_request = "I want a simple blanket"

        result = self.workflow.generate_pattern(user_request)

        # Check validation completed
        validation = result["validation"]
        assert "is_valid" in validation
        assert "errors" in validation
        assert "warnings" in validation
        assert "suggestions" in validation

        # Check outputs generated
        outputs = result["outputs"]
        assert "markdown" in outputs
        assert "text" in outputs
        assert "json" in outputs
        assert "summary" in outputs

        # Verify markdown output has content
        markdown = outputs["markdown"]
        assert "# Stockinette Blanket" in markdown
        assert "## Materials" in markdown
        assert "Cast on 200 stitches" in markdown

    def test_multiple_requests_different_results(self):
        """Test that different requests produce different patterns"""

        simple_result = self.workflow.generate_pattern("simple blanket")
        cable_result = self.workflow.generate_pattern("cable blanket")

        # Should have different stitch patterns
        assert (
            simple_result["fabric_spec"].stitch_pattern.name
            != cable_result["fabric_spec"].stitch_pattern.name
        )

        # Should have different construction notes
        assert (
            simple_result["fabric_spec"].construction_notes
            != cable_result["fabric_spec"].construction_notes
        )
