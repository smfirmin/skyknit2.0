"""
Tests for comprehensive error handling across the knitting pattern generation system.

These tests verify that errors are properly caught, validated, and reported
with meaningful error messages throughout the agent workflow.
"""

import pytest

from src.agents.fabric_agent import FabricAgent
from src.agents.requirements_agent import RequirementsAgent
from src.agents.stitch_agent import StitchAgent
from src.exceptions import (
    DimensionError,
    FabricSpecificationError,
    GaugeError,
    RequirementsParsingError,
    StitchCalculationError,
    ValidationError,
    WorkflowOrchestrationError,
)
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
from src.workflow.pattern_workflow import PatternWorkflow


class TestRequirementsAgentErrorHandling:
    def setup_method(self):
        self.agent = RequirementsAgent()

    def test_empty_user_request_raises_validation_error(self):
        """Test that empty user requests raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"user_request": ""})

        assert "Invalid input data" in str(exc_info.value)
        assert exc_info.value.field == "user_request"

    def test_missing_user_request_raises_validation_error(self):
        """Test that missing user_request key raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"other_key": "value"})

        assert "Invalid input data" in str(exc_info.value)

    def test_non_string_user_request_raises_validation_error(self):
        """Test that non-string user requests raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"user_request": 123})

        assert "Invalid input data" in str(exc_info.value)

    def test_whitespace_only_request_raises_validation_error(self):
        """Test that whitespace-only requests raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"user_request": "   \n\t  "})

        assert "Invalid input data" in str(exc_info.value)


class TestFabricAgentErrorHandling:
    def setup_method(self):
        self.agent = FabricAgent()
        self.valid_requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

    def test_missing_requirements_raises_validation_error(self):
        """Test that missing requirements raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"other_key": "value"})

        assert "Invalid input data" in str(exc_info.value)

    def test_invalid_requirements_type_raises_validation_error(self):
        """Test that invalid requirements type raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"requirements": "not a RequirementsSpec"})

        assert "Invalid input data" in str(exc_info.value)

    def test_unsupported_yarn_weight_raises_gauge_error(self):
        """Test that unsupported yarn weights raise GaugeError"""
        # We need to create a fabric agent with a mock yarn that will cause gauge error
        # Since _determine_yarn_requirements always returns "worsted", we'll test _calculate_gauge directly
        with pytest.raises(GaugeError) as exc_info:
            self.agent._calculate_gauge("unsupported_weight")

        assert "Unsupported yarn weight" in str(exc_info.value)
        assert exc_info.value.yarn_weight == "unsupported_weight"

    def test_empty_yarn_weight_raises_gauge_error(self):
        """Test that empty yarn weights raise GaugeError"""
        with pytest.raises(GaugeError) as exc_info:
            self.agent._calculate_gauge("")

        assert "yarn weight is empty" in str(exc_info.value)


class TestStitchAgentErrorHandling:
    def setup_method(self):
        self.agent = StitchAgent()

        # Create valid test data
        self.fabric_spec = FabricSpec(
            stitch_pattern=StitchPattern("Stockinette", 2, 1, ["K", "P"]),
            border_pattern=StitchPattern("Seed Stitch", 2, 2, ["K1, P1", "P1, K1"]),
            yarn_requirements=YarnSpec("worsted", "wool"),
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=["simple construction"],
        )

        self.construction_spec = ConstructionSpec(
            target_dimensions=Dimensions(width=48.0, length=60.0),
            construction_zones=[
                ConstructionZone(
                    "main_body", self.fabric_spec.stitch_pattern, "center", 2
                )
            ],
            construction_sequence=["cast_on", "main_body", "bind_off"],
            finishing_requirements=["blocking"],
            structural_notes=["work flat"],
        )

    def test_missing_fabric_spec_raises_validation_error(self):
        """Test that missing fabric_spec raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"construction_spec": self.construction_spec})

        assert "Invalid input data" in str(exc_info.value)

    def test_missing_construction_spec_raises_validation_error(self):
        """Test that missing construction_spec raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process({"fabric_spec": self.fabric_spec})

        assert "Invalid input data" in str(exc_info.value)

    def test_invalid_gauge_raises_stitch_calculation_error(self):
        """Test that invalid gauge raises StitchCalculationError"""
        # Create fabric spec with invalid gauge
        invalid_fabric_spec = FabricSpec(
            stitch_pattern=self.fabric_spec.stitch_pattern,
            border_pattern=self.fabric_spec.border_pattern,
            yarn_requirements=self.fabric_spec.yarn_requirements,
            gauge={"stitches_per_inch": 0, "rows_per_inch": 5.5},  # Invalid gauge
            construction_notes=["simple construction"],
        )

        with pytest.raises(StitchCalculationError) as exc_info:
            self.agent.process(
                {
                    "fabric_spec": invalid_fabric_spec,
                    "construction_spec": self.construction_spec,
                }
            )

        assert "Invalid gauge values" in str(exc_info.value)

    def test_negative_dimensions_raise_dimension_error(self):
        """Test that negative dimensions raise DimensionError"""
        # Create construction spec with negative dimensions
        invalid_construction_spec = ConstructionSpec(
            target_dimensions=Dimensions(width=-10.0, length=60.0),  # Invalid width
            construction_zones=self.construction_spec.construction_zones,
            construction_sequence=self.construction_spec.construction_sequence,
            finishing_requirements=self.construction_spec.finishing_requirements,
            structural_notes=self.construction_spec.structural_notes,
        )

        with pytest.raises(DimensionError) as exc_info:
            self.agent.process(
                {
                    "fabric_spec": self.fabric_spec,
                    "construction_spec": invalid_construction_spec,
                }
            )

        assert "Invalid target dimensions" in str(exc_info.value)

    def test_empty_construction_zones_raise_stitch_calculation_error(self):
        """Test that empty construction zones raise StitchCalculationError"""
        # Create construction spec with no zones
        invalid_construction_spec = ConstructionSpec(
            target_dimensions=self.construction_spec.target_dimensions,
            construction_zones=[],  # Empty zones
            construction_sequence=self.construction_spec.construction_sequence,
            finishing_requirements=self.construction_spec.finishing_requirements,
            structural_notes=self.construction_spec.structural_notes,
        )

        with pytest.raises(StitchCalculationError) as exc_info:
            self.agent.process(
                {
                    "fabric_spec": self.fabric_spec,
                    "construction_spec": invalid_construction_spec,
                }
            )

        assert "No construction zones defined" in str(exc_info.value)


class TestWorkflowErrorHandling:
    def setup_method(self):
        self.workflow = PatternWorkflow()

    def test_empty_user_request_raises_workflow_error(self):
        """Test that empty user request raises WorkflowOrchestrationError"""
        with pytest.raises(WorkflowOrchestrationError) as exc_info:
            self.workflow.generate_pattern("")

        assert "Invalid user request" in str(exc_info.value)
        assert exc_info.value.failed_stage == "input_validation"

    def test_none_user_request_raises_workflow_error(self):
        """Test that None user request raises WorkflowOrchestrationError"""
        with pytest.raises(WorkflowOrchestrationError) as exc_info:
            self.workflow.generate_pattern(None)

        assert "Invalid user request" in str(exc_info.value)
        assert exc_info.value.failed_stage == "input_validation"

    def test_non_string_user_request_raises_workflow_error(self):
        """Test that non-string user request raises WorkflowOrchestrationError"""
        with pytest.raises(WorkflowOrchestrationError) as exc_info:
            self.workflow.generate_pattern(123)

        assert "Invalid user request" in str(exc_info.value)
        assert exc_info.value.failed_stage == "input_validation"

    def test_agent_failure_propagates_with_context(self):
        """Test that agent failures are caught and wrapped with context"""
        # This test uses a whitespace-only request to trigger a requirements agent failure
        with pytest.raises(WorkflowOrchestrationError) as exc_info:
            self.workflow.generate_pattern("   ")

        assert "Requirements processing failed" in str(exc_info.value)
        assert exc_info.value.failed_stage == "requirements"
        assert exc_info.value.agent_type == "requirements"


class TestErrorMessageQuality:
    """Test that error messages are clear and actionable"""

    def test_validation_error_has_field_info(self):
        """Test that ValidationError includes field information"""
        agent = RequirementsAgent()

        with pytest.raises(ValidationError) as exc_info:
            agent.process({"user_request": ""})

        error = exc_info.value
        assert error.field == "user_request"
        assert error.expected == "non-empty string"
        assert error.value == ""

    def test_gauge_error_has_yarn_weight_info(self):
        """Test that GaugeError includes yarn weight information"""
        agent = FabricAgent()

        with pytest.raises(GaugeError) as exc_info:
            agent._calculate_gauge("invalid")

        error = exc_info.value
        assert error.yarn_weight == "invalid"

    def test_dimension_error_has_dimension_info(self):
        """Test that DimensionError includes dimension information"""
        agent = StitchAgent()

        # Create valid fabric spec
        fabric_spec = FabricSpec(
            stitch_pattern=StitchPattern("Stockinette", 2, 1, ["K", "P"]),
            border_pattern=None,
            yarn_requirements=YarnSpec("worsted", "wool"),
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=[],
        )

        # Create invalid construction spec to trigger dimension error
        construction_spec = ConstructionSpec(
            target_dimensions=Dimensions(width=-1.0, length=60.0),
            construction_zones=[],
            construction_sequence=[],
            finishing_requirements=[],
            structural_notes=[],
        )

        with pytest.raises(DimensionError) as exc_info:
            agent._validate_calculation_inputs(fabric_spec, construction_spec)

        error = exc_info.value
        assert error.target_dimensions is not None
        assert error.target_dimensions["width"] == -1.0

    def test_workflow_error_has_stage_info(self):
        """Test that WorkflowOrchestrationError includes stage information"""
        workflow = PatternWorkflow()

        with pytest.raises(WorkflowOrchestrationError) as exc_info:
            workflow.generate_pattern(None)

        error = exc_info.value
        assert error.failed_stage == "input_validation"
        assert error.agent_type is None  # No agent involved in input validation


class TestErrorRecovery:
    """Test scenarios where errors should be recoverable or provide guidance"""

    def test_unsupported_yarn_weight_error_lists_supported_weights(self):
        """Test that unsupported yarn weight errors list available options"""
        agent = FabricAgent()

        with pytest.raises(GaugeError) as exc_info:
            agent._calculate_gauge("chunky")

        error_message = str(exc_info.value)
        assert "Supported weights:" in error_message
        assert "worsted" in error_message
        assert "dk" in error_message
        assert "fingering" in error_message

    def test_requirements_parsing_error_includes_user_request(self):
        """Test that requirements parsing errors include the problematic request"""
        agent = RequirementsAgent()

        with pytest.raises(ValidationError) as exc_info:
            agent.process({"user_request": ""})

        # The error should include the problematic value
        assert exc_info.value.value == ""
