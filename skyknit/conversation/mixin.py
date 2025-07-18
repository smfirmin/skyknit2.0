"""
Conversation mixin for agents that support interactive dialogues.

This mixin provides the conversation framework that agents can inherit
to become interactive, while implementing their own domain-specific logic.
"""

import logging
from abc import abstractmethod

from .state import ConversationPhase, ConversationState

logger = logging.getLogger(__name__)


class ConversationMixin:
    """Mixin class that adds conversation capabilities to agents"""

    def start_conversation(self, initial_request: str) -> ConversationState:
        """Start an interactive design conversation with the user"""
        conversation = ConversationState()
        conversation.add_user_message(initial_request)

        # Process the initial request to populate working spec
        self._update_working_spec_from_request(conversation, initial_request)

        # Advance to gathering basics phase
        conversation.advance_phase()

        return conversation

    def continue_conversation(
        self, conversation: ConversationState, user_response: str
    ) -> tuple[ConversationState, str, bool]:
        """Continue an ongoing conversation

        Returns:
            tuple of (updated_conversation, agent_response, is_complete)
        """
        # Add user message to history
        conversation.add_user_message(user_response)
        conversation.iteration_count += 1

        # Update working spec based on new information
        self._update_working_spec_from_request(conversation, user_response)

        # Check if we have enough information
        if conversation.working_spec.is_complete():
            conversation.phase = ConversationPhase.COMPLETE
            agent_response = self._generate_completion_message(conversation)
            conversation.add_agent_message(agent_response)
            return conversation, agent_response, True

        # Generate next question or suggestion
        agent_response = self._generate_next_question(conversation)
        conversation.add_agent_message(agent_response)

        # Advance conversation phase if appropriate
        self._maybe_advance_phase(conversation)

        return conversation, agent_response, False

    def _maybe_advance_phase(self, conversation: ConversationState) -> None:
        """Advance conversation phase based on progress"""
        missing_fields = conversation.working_spec.get_missing_fields()

        # Advance from GATHERING_BASICS if we have basic info
        if (
            conversation.phase == ConversationPhase.GATHERING_BASICS
            and "project_type" not in missing_fields
            and "dimensions" not in missing_fields
        ) or (
            conversation.phase == ConversationPhase.EXPLORING_STYLE
            and "texture_preference" not in missing_fields
            and "complexity_preference" not in missing_fields
        ):
            conversation.advance_phase()

    # Abstract methods that conversation-enabled agents must implement
    @abstractmethod
    def _update_working_spec_from_request(
        self, conversation: ConversationState, request: str
    ) -> None:
        """Update the working spec based on user request

        This should parse the user's message and update the conversation's
        working_spec with any new information found.
        """
        pass

    @abstractmethod
    def _generate_next_question(self, conversation: ConversationState) -> str:
        """Generate the next question to ask the user

        This should look at what information is missing and generate
        an appropriate question to gather that information.
        """
        pass

    @abstractmethod
    def _generate_completion_message(self, conversation: ConversationState) -> str:
        """Generate a completion message when conversation is done

        This should summarize what was gathered and indicate that
        the design is ready to proceed.
        """
        pass
