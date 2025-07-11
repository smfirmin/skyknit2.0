from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentType(Enum):
    REQUIREMENTS = "requirements"
    FABRIC = "fabric"
    CONSTRUCTION = "construction"  # Future use
    STITCH = "stitch"
    VALIDATION = "validation"
    OUTPUT = "output"


@dataclass
class Message:
    sender: AgentType
    recipient: AgentType
    content: Dict[str, Any]
    message_type: str
    timestamp: Optional[str] = None


class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.message_history: List[Message] = []

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return output for this agent"""
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data meets this agent's requirements"""
        pass

    def send_message(
        self, recipient: AgentType, content: Dict[str, Any], message_type: str
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

    def receive_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """Receive and process a message from another agent"""
        if message.recipient != self.agent_type:
            return None

        self.message_history.append(message)
        return self.handle_message(message)

    @abstractmethod
    def handle_message(self, message: Message) -> Dict[str, Any]:
        """Handle a received message"""
        pass
