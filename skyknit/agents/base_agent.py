import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class AgentType(Enum):
    DESIGN = "design"
    FABRIC = "fabric"
    CONSTRUCTION = "construction"  # Future use
    STITCH = "stitch"
    VALIDATION = "validation"
    OUTPUT = "output"


@dataclass
class Message:
    sender: AgentType
    recipient: AgentType
    content: dict[str, Any]
    message_type: str
    timestamp: str | None = None


class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.message_history: list[Message] = []

    @abstractmethod
    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process input and return output for this agent"""
        pass

    @abstractmethod
    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate that input data meets this agent's requirements"""
        pass

    def send_message(
        self, recipient: AgentType, content: dict[str, Any], message_type: str
    ) -> Message:
        """Send a message to another agent"""
        message = Message(
            sender=self.agent_type,
            recipient=recipient,
            content=content,
            message_type=message_type,
        )
        self.message_history.append(message)
        return message

    def receive_message(self, message: Message) -> dict[str, Any] | None:
        """Receive and process a message from another agent"""
        if message.recipient != self.agent_type:
            return None

        self.message_history.append(message)
        return self.handle_message(message)

    @abstractmethod
    def handle_message(self, message: Message) -> dict[str, Any]:
        """Handle a received message"""
        pass

    def _load_system_prompt(self, prompt_filename: str) -> str:
        """Load system prompt from external markdown file"""
        logger = logging.getLogger(__name__)

        try:
            prompt_file = Path(__file__).parent / "prompts" / prompt_filename
            with open(prompt_file, encoding="utf-8") as f:
                content = f.read()

            # Extract the system prompt section
            lines = content.split("\n")
            in_role_section = False
            prompt_lines = []

            for line in lines:
                if line.startswith("## Role"):
                    in_role_section = True
                    continue
                elif line.startswith("## Response Format"):
                    break
                elif in_role_section and not line.startswith("#"):
                    prompt_lines.append(line)

            return "\n".join(prompt_lines).strip()

        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Could not load prompt file {prompt_filename}: {e}")
            return ""

    def _parse_llm_response(
        self, response_text: str, user_request: str
    ) -> dict[str, Any]:
        """Fallback parser for LLM text responses"""
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1

        json_str = response_text[start_idx:end_idx]
        return json.loads(json_str)
