from typing import Any, Dict

from ..exceptions import RequirementsParsingError, ValidationError
from ..models.knitting_models import (
    Dimensions,
    ProjectType,
    RequirementsSpec,
)
from .base_agent import AgentType, BaseAgent, Message


class RequirementsAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.REQUIREMENTS)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse user input into structured requirements"""
        try:
            # Validate input first
            if not self.validate_input(input_data):
                raise ValidationError(
                    "Invalid input data for requirements processing",
                    field="user_request",
                    expected="non-empty string",
                    value=input_data.get("user_request"),
                )

            raw_request = input_data.get("user_request", "")

            # Extract project type
            project_type = self._extract_project_type(raw_request)

            # Extract dimensions
            dimensions = self._extract_dimensions(raw_request, project_type)

            # Extract style preferences
            style_preferences = self._extract_style_preferences(raw_request)

            # Validate extracted requirements
            self._validate_requirements(project_type, dimensions, style_preferences)

            requirements = RequirementsSpec(
                project_type=project_type,
                dimensions=dimensions,
                style_preferences=style_preferences,
                special_requirements=[],
            )

            return {"requirements": requirements}

        except (ValidationError, RequirementsParsingError):
            raise
        except Exception as e:
            raise RequirementsParsingError(
                f"Unexpected error during requirements processing: {str(e)}",
                user_request=raw_request,
            ) from e

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data for requirements processing"""
        if not isinstance(input_data, dict):
            return False

        if "user_request" not in input_data:
            return False

        user_request = input_data["user_request"]
        return isinstance(user_request, str) and len(user_request.strip()) > 0

    def handle_message(self, message: Message) -> Dict[str, Any]:
        return {"status": "acknowledged"}

    def _extract_project_type(self, request: str) -> ProjectType:
        return ProjectType.BLANKET

    def _extract_dimensions(
        self, request: str, project_type: ProjectType
    ) -> Dimensions:
        """Extract dimensions from user request, with validation"""
        try:
            # Simple extraction - in real implementation would use NLP
            # For now, return default dimensions
            width, length = 48.0, 60.0  # default baby blanket

            # Validate dimensions are reasonable
            if width <= 0 or length <= 0:
                raise RequirementsParsingError(
                    f"Invalid dimensions: width={width}, length={length}. "
                    "Dimensions must be positive numbers."
                )

            if width > 200 or length > 200:
                raise RequirementsParsingError(
                    f"Dimensions too large: width={width}, length={length}. "
                    "Maximum supported size is 200 inches."
                )

            return Dimensions(width=width, length=length)

        except RequirementsParsingError:
            raise
        except Exception as e:
            raise RequirementsParsingError(
                f"Failed to extract dimensions from request: {str(e)}",
                user_request=request,
            ) from e

    def _extract_style_preferences(self, request: str) -> Dict[str, str]:
        """Extract style preferences from user request"""
        try:
            # Simple keyword extraction
            preferences = {}
            request_lower = request.lower()

            # Extract texture preference
            if "cable" in request_lower:
                preferences["texture"] = "cable"
            elif "lace" in request_lower:
                preferences["texture"] = "lace"
            else:
                preferences["texture"] = "simple"

            return preferences

        except Exception as e:
            raise RequirementsParsingError(
                f"Failed to extract style preferences: {str(e)}",
                user_request=request,
            ) from e

    def _validate_requirements(
        self,
        project_type: ProjectType,
        dimensions: Dimensions,
        style_preferences: Dict[str, str],
    ) -> None:
        """Validate extracted requirements for consistency and feasibility"""
        # Validate project type is supported
        if project_type not in ProjectType:
            raise RequirementsParsingError(f"Unsupported project type: {project_type}")

        # Validate dimensions are reasonable for project type
        if project_type == ProjectType.BLANKET and (
            dimensions.width < 12 or dimensions.length < 12
        ):
            raise RequirementsParsingError(
                f'Blanket too small: {dimensions.width}" x {dimensions.length}". '
                'Minimum blanket size is 12" x 12".'
            )

        # Validate style preferences contain expected keys
        if "texture" not in style_preferences:
            raise RequirementsParsingError(
                "Missing texture preference in style preferences"
            )

        # Validate texture is supported
        supported_textures = {"simple", "cable", "lace"}
        texture = style_preferences["texture"]
        if texture not in supported_textures:
            raise RequirementsParsingError(
                f"Unsupported texture: {texture}. "
                f"Supported textures: {', '.join(supported_textures)}"
            )
