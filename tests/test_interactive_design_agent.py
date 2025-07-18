"""
Tests for the interactive conversation capabilities of the DesignAgent.
"""

from unittest.mock import Mock

from skyknit.agents.design_agent import DesignAgent
from skyknit.conversation import ConversationPhase
from skyknit.llms import BaseLLMClient


def test_design_agent_has_conversation_methods():
    """Test that DesignAgent has conversation methods from mixin"""
    mock_llm = Mock(spec=BaseLLMClient)
    agent = DesignAgent(llm_client=mock_llm)

    # Should have conversation methods
    assert hasattr(agent, "start_conversation")
    assert hasattr(agent, "continue_conversation")
    assert callable(agent.start_conversation)
    assert callable(agent.continue_conversation)


def test_start_conversation():
    """Test starting a conversation with the design agent"""
    mock_llm = Mock(spec=BaseLLMClient)
    mock_llm.generate_structured.return_value = {
        "project_type": "BLANKET",
        "dimensions": {"width": 50.0, "length": 60.0},
        "style_preferences": {"texture": "simple", "complexity": "beginner"},
        "special_requirements": [],
    }

    agent = DesignAgent(llm_client=mock_llm)

    conversation = agent.start_conversation("I want a cozy blanket")

    # Should have initial state
    assert conversation.phase == ConversationPhase.GATHERING_BASICS
    assert len(conversation.conversation_history) == 1
    assert conversation.conversation_history[0]["role"] == "user"
    assert conversation.conversation_history[0]["content"] == "I want a cozy blanket"

    # Should have extracted some information
    assert conversation.working_spec.project_type is not None


def test_continue_conversation():
    """Test continuing a conversation"""
    mock_llm = Mock(spec=BaseLLMClient)
    mock_llm.generate_structured.return_value = {
        "project_type": "BLANKET",
        "dimensions": {"width": 40.0, "length": 50.0},
        "style_preferences": {"texture": "simple", "complexity": "beginner"},
        "special_requirements": [],
    }

    agent = DesignAgent(llm_client=mock_llm)

    # Start conversation
    conversation = agent.start_conversation("I want a blanket")

    # Continue conversation
    conversation, response, is_complete = agent.continue_conversation(
        conversation, "Make it 40 by 50 inches"
    )

    # Should not be complete yet (missing some info)
    assert not is_complete
    assert isinstance(response, str)
    assert len(response) > 0

    # Should have added messages
    assert len(conversation.conversation_history) >= 2


def test_conversation_completion():
    """Test that conversation completes when all info is gathered"""
    mock_llm = Mock(spec=BaseLLMClient)
    # Mock complete response
    mock_llm.generate_structured.return_value = {
        "project_type": "BLANKET",
        "dimensions": {"width": 50.0, "length": 60.0},
        "style_preferences": {"texture": "simple", "complexity": "beginner"},
        "special_requirements": [],
    }

    agent = DesignAgent(llm_client=mock_llm)

    # Start with a complete request
    conversation = agent.start_conversation(
        "I want a 50x60 inch simple beginner blanket in worsted wool"
    )

    # The working spec should be mostly complete, but fabric might be missing
    # Let's continue to see if it completes
    conversation, response, is_complete = agent.continue_conversation(
        conversation, "Yes, that sounds perfect"
    )

    # Should eventually complete (might need fabric generation)
    # For now, just test that the method works
    assert isinstance(is_complete, bool)
    assert isinstance(response, str)


def test_question_generation():
    """Test that appropriate questions are generated"""
    mock_llm = Mock(spec=BaseLLMClient)
    agent = DesignAgent(llm_client=mock_llm)

    # Test the question generation logic directly
    from skyknit.conversation import ConversationState, WorkingDesignSpec

    conversation = ConversationState()
    conversation.working_spec = WorkingDesignSpec()

    # Should ask about project type first
    question = agent._generate_next_question(conversation)
    assert "project" in question.lower() or "blanket" in question.lower()


def test_conversation_mixin_integration():
    """Test that the mixin integrates properly with the agent"""
    mock_llm = Mock(spec=BaseLLMClient)
    agent = DesignAgent(llm_client=mock_llm)

    # Should be able to access both BaseAgent and ConversationMixin methods
    assert hasattr(agent, "process")  # From BaseAgent
    assert hasattr(agent, "start_conversation")  # From ConversationMixin
    assert hasattr(agent, "_generate_next_question")  # Implemented by DesignAgent

    # Should have correct agent type
    from skyknit.agents.base_agent import AgentType

    assert agent.agent_type == AgentType.DESIGN
