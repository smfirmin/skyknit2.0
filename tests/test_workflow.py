import pytest

from src.models.knitting_models import ProjectType
from src.workflow.pattern_workflow import PatternWorkflow


class TestPatternWorkflow:
    def setup_method(self):
        self.workflow = PatternWorkflow()

    def test_initialization(self):
        assert self.workflow.requirements_agent is not None
        assert self.workflow.fabric_agent is not None
        assert self.workflow.construction_agent is not None
        assert self.workflow.stitch_agent is not None
        assert self.workflow.validation_agent is not None
        assert self.workflow.output_agent is not None

    def test_validate_workflow(self):
        assert self.workflow.validate_workflow() is True

    def test_generate_pattern_returns_complete_result(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        # Check all expected keys are present
        expected_keys = [
            "user_request",
            "requirements",
            "fabric_spec",
            "construction_spec",
            "stitch_result",
            "validation",
            "outputs",
            "pattern_summary",
        ]

        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_generate_pattern_preserves_user_request(self):
        user_request = "I want a cable blanket"
        result = self.workflow.generate_pattern(user_request)

        assert result["user_request"] == user_request

    def test_generate_pattern_requirements_stage(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        requirements = result["requirements"]
        assert requirements.project_type == ProjectType.BLANKET
        assert hasattr(requirements, "dimensions")
        assert hasattr(requirements, "style_preferences")

    def test_generate_pattern_fabric_stage(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        fabric_spec = result["fabric_spec"]
        assert hasattr(fabric_spec, "stitch_pattern")
        assert hasattr(fabric_spec, "yarn_requirements")
        assert hasattr(fabric_spec, "gauge")
        assert hasattr(fabric_spec, "construction_notes")

    def test_generate_pattern_construction_stage(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        construction_spec = result["construction_spec"]
        assert hasattr(construction_spec, "target_dimensions")
        assert hasattr(construction_spec, "construction_zones")
        assert hasattr(construction_spec, "construction_sequence")

    def test_generate_pattern_stitch_stage(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        stitch_result = result["stitch_result"]
        assert "cast_on_stitches" in stitch_result
        assert "total_rows" in stitch_result
        assert "actual_dimensions" in stitch_result
        assert "stitch_instructions" in stitch_result

    def test_generate_pattern_validation_stage(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        validation = result["validation"]
        assert "is_valid" in validation
        assert "errors" in validation
        assert "warnings" in validation
        assert "suggestions" in validation

    def test_generate_pattern_output_stage(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        outputs = result["outputs"]
        assert "markdown" in outputs
        assert "text" in outputs
        assert "json" in outputs
        assert "summary" in outputs

    def test_generate_pattern_summary_stage(self):
        user_request = "I want a simple blanket"
        result = self.workflow.generate_pattern(user_request)

        pattern_summary = result["pattern_summary"]
        assert "title" in pattern_summary
        assert "project_type" in pattern_summary
        assert "materials" in pattern_summary
        assert "cast_on_stitches" in pattern_summary

    def test_different_requests_produce_different_patterns(self):
        simple_result = self.workflow.generate_pattern("simple blanket")
        cable_result = self.workflow.generate_pattern("cable blanket")

        # Should have different style preferences
        assert (
            simple_result["requirements"].style_preferences["texture"]
            != cable_result["requirements"].style_preferences["texture"]
        )

        # Should have different stitch patterns
        assert (
            simple_result["fabric_spec"].stitch_pattern.name
            != cable_result["fabric_spec"].stitch_pattern.name
        )

    def test_workflow_error_handling(self):
        from src.exceptions import WorkflowOrchestrationError

        # Test with empty request - should now raise error
        with pytest.raises(WorkflowOrchestrationError) as exc_info:
            self.workflow.generate_pattern("")

        assert "Invalid user request" in str(exc_info.value)
        assert exc_info.value.failed_stage == "input_validation"

    def test_agent_dependencies(self):
        # Test that each stage depends on the previous stage's output
        user_request = "I want a simple blanket"

        # Requirements stage
        req_result = self.workflow.requirements_agent.process(
            {"user_request": user_request}
        )
        assert "requirements" in req_result

        # Fabric stage depends on requirements
        fabric_result = self.workflow.fabric_agent.process(req_result)
        assert "fabric_spec" in fabric_result

        # This validates the dependency chain works
        assert fabric_result["fabric_spec"].stitch_pattern is not None
