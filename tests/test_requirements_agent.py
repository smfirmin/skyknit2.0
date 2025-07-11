import pytest

from src.agents.base_agent import AgentType, Message
from src.agents.requirements_agent import RequirementsAgent
from src.models.knitting_models import Dimensions, ProjectType


class TestRequirementsAgent:
    def setup_method(self):
        self.agent = RequirementsAgent()

    def test_initialization(self):
        assert self.agent.agent_type == AgentType.REQUIREMENTS

    def test_validate_input_valid(self):
        valid_input = {"user_request": "I want a simple blanket"}
        assert self.agent.validate_input(valid_input) is True

    def test_validate_input_missing_request(self):
        invalid_input = {"other_key": "value"}
        assert self.agent.validate_input(invalid_input) is False

    def test_validate_input_wrong_type(self):
        invalid_input = {"user_request": 123}
        assert self.agent.validate_input(invalid_input) is False

    def test_process_simple_request(self):
        input_data = {"user_request": "I want a simple blanket"}
        result = self.agent.process(input_data)

        assert "requirements" in result
        requirements = result["requirements"]

        assert requirements.project_type == ProjectType.BLANKET
        assert requirements.dimensions.width == 48.0
        assert requirements.dimensions.length == 60.0
        assert requirements.style_preferences["texture"] == "simple"
        assert requirements.special_requirements == []

    def test_process_cable_request(self):
        input_data = {"user_request": "I want a cable blanket"}
        result = self.agent.process(input_data)

        requirements = result["requirements"]
        assert requirements.style_preferences["texture"] == "cable"

    def test_process_lace_request(self):
        input_data = {"user_request": "I want a lace blanket"}
        result = self.agent.process(input_data)

        requirements = result["requirements"]
        assert requirements.style_preferences["texture"] == "lace"

    def test_extract_project_type(self):
        # Currently always returns BLANKET
        result = self.agent._extract_project_type("any request")
        assert result == ProjectType.BLANKET

    def test_extract_dimensions(self):
        # Currently returns default dimensions
        result = self.agent._extract_dimensions("any request", ProjectType.BLANKET)
        assert isinstance(result, Dimensions)
        assert result.width == 48.0
        assert result.length == 60.0

    def test_extract_style_preferences_simple(self):
        result = self.agent._extract_style_preferences("simple blanket")
        assert result["texture"] == "simple"

    def test_extract_style_preferences_cable(self):
        result = self.agent._extract_style_preferences("cable blanket")
        assert result["texture"] == "cable"

    def test_extract_style_preferences_lace(self):
        result = self.agent._extract_style_preferences("lace blanket")
        assert result["texture"] == "lace"

    def test_extract_style_preferences_case_insensitive(self):
        result = self.agent._extract_style_preferences("CABLE BLANKET")
        assert result["texture"] == "cable"

    def test_handle_message(self):
        message = Message(
            sender=AgentType.FABRIC,
            recipient=AgentType.REQUIREMENTS,
            content={"test": "data"},
            message_type="test",
        )
        result = self.agent.handle_message(message)
        assert result["status"] == "acknowledged"

    def test_process_empty_request(self):
        from src.exceptions import ValidationError

        input_data = {"user_request": ""}

        # Should raise ValidationError for empty request
        with pytest.raises(ValidationError) as exc_info:
            self.agent.process(input_data)

        assert "Invalid input data" in str(exc_info.value)
        assert exc_info.value.field == "user_request"

    def test_process_multiple_keywords(self):
        input_data = {"user_request": "I want a cable and lace blanket"}
        result = self.agent.process(input_data)

        # Should prioritize cable over lace based on order in method
        requirements = result["requirements"]
        assert requirements.style_preferences["texture"] == "cable"
