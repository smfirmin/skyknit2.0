"""
Conversation state management for interactive design agent.

This module handles tracking the state of an ongoing conversation between
the user and the design agent, including what information has been gathered
and what still needs to be clarified.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from skyknit.models.knitting_models import (
    DesignSpec,
    Dimensions,
    FabricSpec,
    ProjectType,
)


class ConversationPhase(Enum):
    """Phases of the design conversation"""

    INITIAL = "initial"
    GATHERING_BASICS = "gathering_basics"
    EXPLORING_STYLE = "exploring_style"
    REFINING_DETAILS = "refining_details"
    CONFIRMING_DESIGN = "confirming_design"
    COMPLETE = "complete"


@dataclass
class WorkingDesignSpec:
    """Holds partially completed design information during conversation.

    This mirrors FinalDesignSpec (DesignSpec) but with Optional fields
    plus conversation-specific metadata.
    """

    # Core design fields (Optional versions of FinalDesignSpec fields)
    project_type: ProjectType | None = None
    dimensions: Dimensions | None = None
    fabric: FabricSpec | None = None
    style_preferences: dict[str, Any] = field(default_factory=dict)
    special_requirements: list[str] = field(default_factory=list)

    # Conversation-specific metadata
    confidence_scores: dict[str, float] = field(default_factory=dict)
    user_feedback: list[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Check if we have enough information to create a FinalDesignSpec"""
        return all(
            [
                self.project_type is not None,
                self.dimensions is not None,
                self.fabric is not None,
                self.style_preferences.get("texture"),
                self.style_preferences.get("complexity"),
            ]
        )

    def get_missing_fields(self) -> list[str]:
        """Get list of fields that still need to be gathered"""
        missing = []
        if self.project_type is None:
            missing.append("project_type")
        if self.dimensions is None:
            missing.append("dimensions")
        if self.fabric is None:
            missing.append("fabric")
        if not self.style_preferences.get("texture"):
            missing.append("texture_preference")
        if not self.style_preferences.get("complexity"):
            missing.append("complexity_preference")
        return missing

    def to_final_design_spec(self) -> DesignSpec:
        """Convert to complete FinalDesignSpec, raising error if incomplete"""
        if not self.is_complete():
            raise ValueError(
                f"Cannot create FinalDesignSpec: missing fields {self.get_missing_fields()}"
            )

        return DesignSpec(
            project_type=self.project_type,
            dimensions=self.dimensions,
            fabric=self.fabric,
            style_preferences=self.style_preferences,
            special_requirements=self.special_requirements,
        )


@dataclass
class ConversationState:
    """Tracks the complete state of a design conversation"""

    phase: ConversationPhase = ConversationPhase.INITIAL
    working_spec: WorkingDesignSpec = field(default_factory=WorkingDesignSpec)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    pending_questions: list[str] = field(default_factory=list)
    suggestions_made: list[dict[str, Any]] = field(default_factory=list)
    iteration_count: int = 0

    def add_user_message(self, message: str):
        """Add a user message to the conversation history"""
        self.conversation_history.append({"role": "user", "content": message})

    def add_agent_message(self, message: str):
        """Add an agent message to the conversation history"""
        self.conversation_history.append({"role": "agent", "content": message})

    def advance_phase(self):
        """Move to the next conversation phase"""
        phases = list(ConversationPhase)
        current_index = phases.index(self.phase)
        if current_index < len(phases) - 1:
            self.phase = phases[current_index + 1]

    def should_ask_clarifying_questions(self) -> bool:
        """Determine if we need to ask clarifying questions"""
        return len(self.working_spec.get_missing_fields()) > 0 or self.phase in [
            ConversationPhase.GATHERING_BASICS,
            ConversationPhase.EXPLORING_STYLE,
        ]

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation so far"""
        summary_parts = []
        if self.working_spec.project_type:
            summary_parts.append(f"Project: {self.working_spec.project_type.value}")
        if self.working_spec.dimensions:
            dims = self.working_spec.dimensions
            summary_parts.append(f'Size: {dims.width}" x {dims.length}"')
        if self.working_spec.style_preferences:
            prefs = []
            for key, value in self.working_spec.style_preferences.items():
                if value:
                    prefs.append(f"{key}: {value}")
            if prefs:
                summary_parts.append(f"Style: {', '.join(prefs)}")

        return " | ".join(summary_parts) if summary_parts else "No details gathered yet"
