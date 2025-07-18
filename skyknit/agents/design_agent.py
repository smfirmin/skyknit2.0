"""
LLM-powered Design Agent for knitting pattern generation.

This agent uses LLMs with RAG to parse natural language requests into
structured knitting design requirements.
"""

import logging
from typing import Any

from skyknit.agents.base_agent import AgentType, BaseAgent
from skyknit.agents.prompts import DESIGN_SCHEMA
from skyknit.conversation import (
    ConversationMixin,
    ConversationState,
)
from skyknit.knowledge_base import FabricKnowledgeBase, KnowledgeBaseDB
from skyknit.llms import BaseLLMClient
from skyknit.models.knitting_models import (
    DesignSpec,
    Dimensions,
    FabricSpec,
    ProjectType,
    StitchPattern,
    YarnSpec,
    YarnWeight,
)

logger = logging.getLogger(__name__)


class DesignAgent(BaseAgent, ConversationMixin):
    """LLM-powered agent for parsing user design requirements"""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        knowledge_base_path: str | None = None,
    ):
        """
        Initialize LLM Design Agent.

        Args:
            llm_client: LLM client to use (required)
            knowledge_base_path: Path to knowledge base database
        """
        super().__init__(AgentType.DESIGN)

        # Initialize LLM client
        if llm_client is None:
            raise ValueError(
                "LLM client is required. Use LLMClient.create_anthropic() "
                "or LLMClient.create_ollama()"
            )
        self.llm_client = llm_client

        # Initialize knowledge base for RAG
        self.knowledge_base = None
        self.fabric_knowledge = FabricKnowledgeBase()

        if knowledge_base_path:
            self.knowledge_base = KnowledgeBaseDB(knowledge_base_path)

        # Initialize gauge map for fabric decisions
        self.gauge_map = {
            YarnWeight.WORSTED: {"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            YarnWeight.DK: {"stitches_per_inch": 5.0, "rows_per_inch": 6.0},
            YarnWeight.FINGERING: {"stitches_per_inch": 7.0, "rows_per_inch": 8.0},
            YarnWeight.BULKY: {"stitches_per_inch": 3.0, "rows_per_inch": 4.0},
            YarnWeight.SPORT: {"stitches_per_inch": 6.0, "rows_per_inch": 7.0},
        }

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process user request using LLM with RAG"""
        user_request = input_data["user_request"]

        # Use RAG to enhance the request with relevant knowledge
        enhanced_context = self._get_rag_context(user_request)

        # Generate structured requirements using LLM
        requirements_data = self._extract_requirements_with_llm(
            user_request, enhanced_context
        )

        # Generate fabric specifications
        fabric_spec = self._generate_fabric_spec(
            requirements_data, user_request, enhanced_context
        )

        # Convert to DesignSpec (includes both requirements and fabric)
        design_spec = self._create_design_spec(requirements_data, fabric_spec)

        # Validate the generated design
        self._validate_design_spec(design_spec)

        return {"design_spec": design_spec}

    def _get_rag_context(self, user_request: str) -> str:
        """Get relevant fabric knowledge context for requirements parsing"""
        context_parts = []

        # Add general fabric knowledge relevant to the request
        # This helps the LLM understand fabric behavior for requirements parsing
        warmth_words = ["warm", "cold", "summer", "winter"]
        if any(word in user_request.lower() for word in warmth_words):
            context_parts.append("WARMTH KNOWLEDGE:")
            context_parts.append(self.fabric_knowledge.get_knowledge_for_llm("warmth"))

        drape_words = ["drape", "flow", "structure", "stiff"]
        if any(word in user_request.lower() for word in drape_words):
            context_parts.append("DRAPE KNOWLEDGE:")
            context_parts.append(self.fabric_knowledge.get_knowledge_for_llm("drape"))

        gauge_words = ["gauge", "tight", "loose", "thick", "thin"]
        if any(word in user_request.lower() for word in gauge_words):
            context_parts.append("GAUGE KNOWLEDGE:")
            context_parts.append(self.fabric_knowledge.get_knowledge_for_llm("gauge"))

        return "\n".join(context_parts)

    def _extract_requirements_with_llm(
        self, user_request: str, context: str
    ) -> dict[str, Any]:
        """Extract structured requirements using LLM"""

        system_prompt = self._load_system_prompt("design_agent_prompt.md")
        user_prompt = f"""User Request: "{user_request}"

        Additional Context:
        {context}

        Please extract the knitting project requirements and respond with
        valid JSON matching this exact structure:
        {{
            "project_type": "BLANKET",
            "dimensions": {{
                "width": number_in_inches,
                "length": number_in_inches
            }},
            "style_preferences": {{
                "texture": "simple|textured|cable|lace|colorwork",
                "complexity": "beginner|intermediate|advanced"
            }},
            "special_requirements": ["list", "of", "special", "requirements"]
        }}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            return self.llm_client.generate_structured(messages, DESIGN_SCHEMA)
        except Exception as e:
            logger.error(f"LLM structured generation failed: {e}")
            # Fallback to text generation and manual parsing
            response_text = self.llm_client.generate(messages)
            return self._parse_llm_response(response_text, user_request)

    def _generate_fabric_spec(
        self,
        requirements_data: dict[str, Any],
        user_request: str,
        enhanced_context: str,
    ) -> FabricSpec:
        """Generate fabric specification based on requirements and context"""
        style_prefs = requirements_data.get("style_preferences", {})
        complexity = style_prefs.get("complexity")
        texture = style_prefs.get("texture")

        # Determine yarn weight based on user request and complexity
        yarn_weight = None
        request_lower = user_request.lower()

        # Check for explicit yarn weight mentions
        if "worsted" in request_lower:
            yarn_weight = YarnWeight.WORSTED
        elif "dk" in request_lower or "double knit" in request_lower:
            yarn_weight = YarnWeight.DK
        elif "fingering" in request_lower:
            yarn_weight = YarnWeight.FINGERING
        elif "sport" in request_lower:
            yarn_weight = YarnWeight.SPORT
        elif "bulky" in request_lower:
            yarn_weight = YarnWeight.BULKY
        elif "aran" in request_lower:
            yarn_weight = YarnWeight.ARAN

        # If no explicit weight mentioned, infer from complexity and project type
        if not yarn_weight and complexity:
            if complexity == "beginner":
                yarn_weight = YarnWeight.WORSTED  # Easier to work with
            elif complexity == "intermediate":
                yarn_weight = YarnWeight.DK  # Good balance
            elif complexity == "advanced":
                yarn_weight = YarnWeight.FINGERING  # More detailed work

        # If still no yarn weight determined, raise error to force clarification
        if not yarn_weight:
            raise ValueError(
                "Yarn weight not specified. Please specify yarn weight (worsted, dk, fingering, sport, bulky, etc.)"
            )

        # Determine fiber based on user request
        fiber = None
        if "wool" in request_lower:
            fiber = "wool"
        elif "cotton" in request_lower:
            fiber = "cotton"
        elif "acrylic" in request_lower:
            fiber = "acrylic"
        elif "alpaca" in request_lower:
            fiber = "alpaca"
        elif "bamboo" in request_lower:
            fiber = "bamboo"
        elif "silk" in request_lower:
            fiber = "silk"

        # If no fiber specified, raise error to force clarification
        if not fiber:
            raise ValueError(
                "Yarn fiber not specified. Please specify fiber type (wool, cotton, acrylic, alpaca, etc.)"
            )

        yarn_spec = YarnSpec(weight=yarn_weight, fiber=fiber)

        # Create stitch pattern based on texture preference
        stitch_pattern = None
        if texture == "simple":
            stitch_pattern = StitchPattern(
                name="Stockinette",
                row_repeat=2,
                stitch_repeat=1,
                instructions=["Row 1: Knit all stitches", "Row 2: Purl all stitches"],
            )
        elif texture == "textured":
            stitch_pattern = StitchPattern(
                name="Seed Stitch",
                row_repeat=2,
                stitch_repeat=2,
                instructions=[
                    "Row 1: *K1, P1; repeat from *",
                    "Row 2: *P1, K1; repeat from *",
                ],
            )
        elif texture == "cable":
            stitch_pattern = StitchPattern(
                name="Simple Cable",
                row_repeat=8,
                stitch_repeat=8,
                instructions=[
                    "Rows 1, 3, 5, 7: *K2, P4, K2; repeat from *",
                    "Rows 2, 4, 6, 8: *P2, K4, P2; repeat from *",
                    "Row 9: *K2, C4F, K2; repeat from *",
                    "Row 10: *P2, K4, P2; repeat from *",
                ],
            )
        elif texture == "lace":
            stitch_pattern = StitchPattern(
                name="Simple Lace",
                row_repeat=4,
                stitch_repeat=6,
                instructions=[
                    "Row 1: *K1, YO, K2tog, K1, SSK, YO; repeat from *",
                    "Row 2: Purl all stitches",
                    "Row 3: *YO, K2tog, K2, SSK, YO; repeat from *",
                    "Row 4: Purl all stitches",
                ],
            )

        if not stitch_pattern:
            raise ValueError(
                "Texture preference not specified or not supported. Please specify: simple, textured, cable, or lace"
            )

        # Get gauge from the gauge map
        gauge = self.gauge_map.get(yarn_weight)
        if not gauge:
            raise ValueError(f"Gauge not defined for yarn weight '{yarn_weight.value}'")

        return FabricSpec(
            stitch_pattern=stitch_pattern,
            yarn_requirements=yarn_spec,
            gauge=gauge,
            border_pattern=None,
        )

    def _create_design_spec(
        self, requirements_data: dict[str, Any], fabric_spec: FabricSpec
    ) -> DesignSpec:
        """Convert parsed data and fabric spec to DesignSpec"""
        project_type = ProjectType[requirements_data["project_type"]]

        # Create dimensions
        dimensions = Dimensions(
            width=float(requirements_data["dimensions"]["width"]),
            length=float(requirements_data["dimensions"]["length"]),
        )

        # Extract style preferences and special requirements
        style_preferences = requirements_data.get("style_preferences", {})
        special_requirements = requirements_data.get("special_requirements", [])

        return DesignSpec(
            project_type=project_type,
            dimensions=dimensions,
            fabric=fabric_spec,
            style_preferences=style_preferences,
            special_requirements=special_requirements,
        )

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data for design processing"""
        if not isinstance(input_data, dict):
            return False

        user_request = input_data.get("user_request", "")
        return isinstance(user_request, str) and user_request.strip()

    def handle_message(self, message) -> dict[str, Any]:
        """Handle messages from other agents"""
        return {"status": "acknowledged"}

    def _update_working_spec_from_request(
        self, conversation: ConversationState, request: str
    ) -> None:
        """Update the working spec based on user request"""
        try:
            # Use RAG to enhance the request
            enhanced_context = self._get_rag_context(request)

            # Extract requirements using LLM
            requirements_data = self._extract_requirements_with_llm(
                request, enhanced_context
            )

            # Update working spec with any new information
            if "project_type" in requirements_data:
                project_type_str = requirements_data["project_type"]
                conversation.working_spec.project_type = ProjectType[project_type_str]

            if "dimensions" in requirements_data:
                dims_data = requirements_data["dimensions"]
                conversation.working_spec.dimensions = Dimensions(
                    width=float(dims_data["width"]), length=float(dims_data["length"])
                )

            if "style_preferences" in requirements_data:
                conversation.working_spec.style_preferences.update(
                    requirements_data["style_preferences"]
                )

            if "special_requirements" in requirements_data:
                conversation.working_spec.special_requirements.extend(
                    requirements_data["special_requirements"]
                )

            # Try to update fabric spec with any new information
            self._update_partial_fabric_spec(
                conversation, requirements_data, request, enhanced_context
            )

        except Exception as e:
            logger.warning(f"Failed to extract requirements from request: {e}")
            # Continue conversation even if extraction fails

    def _update_partial_fabric_spec(
        self,
        conversation: ConversationState,
        requirements_data: dict[str, Any],
        request: str,
        enhanced_context: str,
    ) -> None:
        """Update fabric spec with partial information from user request"""
        # Get current fabric spec or create new one
        current_fabric = conversation.working_spec.fabric

        # Extract yarn weight if mentioned
        yarn_weight = self._extract_yarn_weight_from_request(request)

        # Extract fiber if mentioned
        fiber = self._extract_fiber_from_request(request)

        # Extract texture from style preferences
        style_prefs = requirements_data.get("style_preferences", {})
        texture = style_prefs.get("texture")

        # If we have any new fabric information, update or create fabric spec
        if yarn_weight or fiber or texture:
            # Start with current values or None
            final_yarn_weight = yarn_weight
            final_fiber = fiber
            final_stitch_pattern = None

            if current_fabric:
                # Keep existing values if no new ones provided
                if not yarn_weight:
                    final_yarn_weight = current_fabric.yarn_requirements.weight
                if not fiber:
                    final_fiber = current_fabric.yarn_requirements.fiber
                if not texture:
                    final_stitch_pattern = current_fabric.stitch_pattern

            # Create yarn spec if we have both weight and fiber
            yarn_spec = None
            if final_yarn_weight and final_fiber:
                yarn_spec = YarnSpec(weight=final_yarn_weight, fiber=final_fiber)

            # Create stitch pattern if we have texture
            if texture and not final_stitch_pattern:
                final_stitch_pattern = self._create_stitch_pattern_for_texture(texture)

            # Create fabric spec if we have enough information
            if yarn_spec and final_stitch_pattern:
                gauge = self.gauge_map.get(final_yarn_weight, {})
                conversation.working_spec.fabric = FabricSpec(
                    stitch_pattern=final_stitch_pattern,
                    yarn_requirements=yarn_spec,
                    gauge=gauge,
                    border_pattern=None,
                )

    def _extract_yarn_weight_from_request(self, request: str) -> YarnWeight | None:
        """Extract yarn weight from user request"""
        request_lower = request.lower()
        if "worsted" in request_lower:
            return YarnWeight.WORSTED
        elif "dk" in request_lower or "double knit" in request_lower:
            return YarnWeight.DK
        elif "fingering" in request_lower:
            return YarnWeight.FINGERING
        elif "sport" in request_lower:
            return YarnWeight.SPORT
        elif "bulky" in request_lower:
            return YarnWeight.BULKY
        elif "aran" in request_lower:
            return YarnWeight.ARAN
        return None

    def _extract_fiber_from_request(self, request: str) -> str | None:
        """Extract fiber type from user request"""
        request_lower = request.lower()
        if "wool" in request_lower:
            return "wool"
        elif "cotton" in request_lower:
            return "cotton"
        elif "acrylic" in request_lower:
            return "acrylic"
        elif "alpaca" in request_lower:
            return "alpaca"
        elif "bamboo" in request_lower:
            return "bamboo"
        elif "silk" in request_lower:
            return "silk"
        return None

    def _create_stitch_pattern_for_texture(self, texture: str) -> StitchPattern:
        """Create a stitch pattern based on texture preference"""
        if texture == "simple":
            return StitchPattern(
                name="Stockinette",
                row_repeat=2,
                stitch_repeat=1,
                instructions=[
                    "Row 1: Knit all stitches",
                    "Row 2: Purl all stitches",
                ],
            )
        elif texture == "textured":
            return StitchPattern(
                name="Seed Stitch",
                row_repeat=2,
                stitch_repeat=2,
                instructions=[
                    "Row 1: *K1, P1; repeat from *",
                    "Row 2: *P1, K1; repeat from *",
                ],
            )
        elif texture == "cable":
            return StitchPattern(
                name="Simple Cable",
                row_repeat=8,
                stitch_repeat=8,
                instructions=[
                    "Rows 1, 3, 5, 7: *K2, P4, K2; repeat from *",
                    "Rows 2, 4, 6, 8: *P2, K4, P2; repeat from *",
                    "Row 9: *K2, C4F, K2; repeat from *",
                    "Row 10: *P2, K4, P2; repeat from *",
                ],
            )
        elif texture == "lace":
            return StitchPattern(
                name="Simple Lace",
                row_repeat=4,
                stitch_repeat=6,
                instructions=[
                    "Row 1: *K1, YO, K2tog, K1, SSK, YO; repeat from *",
                    "Row 2: Purl all stitches",
                    "Row 3: *YO, K2tog, K2, SSK, YO; repeat from *",
                    "Row 4: Purl all stitches",
                ],
            )
        else:
            # Default to simple for unknown textures
            return StitchPattern(
                name="Stockinette",
                row_repeat=2,
                stitch_repeat=1,
                instructions=[
                    "Row 1: Knit all stitches",
                    "Row 2: Purl all stitches",
                ],
            )

    def _generate_next_question(self, conversation: ConversationState) -> str:
        """Generate the next question to ask the user"""
        missing_fields = conversation.working_spec.get_missing_fields()

        if "project_type" in missing_fields:
            return "What type of knitting project would you like to create? (Currently I can help with blankets)"

        if "dimensions" in missing_fields:
            return "What size would you like your blanket to be? Please provide width and length in inches."

        if "texture_preference" in missing_fields:
            return "What texture or style are you looking for? For example: simple/smooth, textured, cable patterns, or lace?"

        if "complexity_preference" in missing_fields:
            return "What's your skill level? Would you prefer a beginner, intermediate, or advanced pattern?"

        if "fabric" in missing_fields:
            # Check what specific fabric info is missing
            current_fabric = conversation.working_spec.fabric
            if not current_fabric:
                return (
                    "Do you have any preferences for yarn weight or fiber? "
                    "(e.g., worsted wool, dk cotton, etc.)"
                )
            elif not hasattr(current_fabric, "yarn_requirements"):
                return (
                    "What yarn would you like to use? "
                    "Please specify weight and fiber type."
                )
            else:
                return (
                    "What yarn preferences do you have? "
                    "(weight like worsted/dk, fiber like wool/cotton)"
                )

        # If we get here, we should have most information
        summary = conversation.get_conversation_summary()
        return (
            f"Let me confirm what we have so far: {summary}. "
            "Is this correct, or would you like to change anything?"
        )

    def _generate_completion_message(self, conversation: ConversationState) -> str:
        """Generate a completion message when conversation is done"""
        summary = conversation.get_conversation_summary()
        return f"Perfect! I have everything I need to create your design: {summary}. Your knitting pattern is ready to be generated!"

    def close(self):
        """Clean up resources"""
        if self.knowledge_base:
            self.knowledge_base.close()
