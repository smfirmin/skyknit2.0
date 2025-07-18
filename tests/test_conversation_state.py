"""
Tests for conversation state management.
"""

import pytest

from skyknit.conversation import ConversationPhase, ConversationState, WorkingDesignSpec
from skyknit.models.knitting_models import (
    DesignSpec,
    Dimensions,
    FabricSpec,
    ProjectType,
    StitchPattern,
    YarnSpec,
    YarnWeight,
)


def test_working_and_final_design_spec_compatibility():
    """Ensure WorkingDesignSpec can convert to FinalDesignSpec (DesignSpec)"""
    # Get field names from both classes
    working_fields = set(WorkingDesignSpec.__dataclass_fields__.keys())
    final_fields = set(DesignSpec.__dataclass_fields__.keys())

    # Remove conversation-specific fields from comparison
    conversation_only_fields = {"confidence_scores", "user_feedback"}
    working_core_fields = working_fields - conversation_only_fields

    # Check that all FinalDesignSpec fields exist in WorkingDesignSpec
    missing = final_fields - working_core_fields
    assert not missing, f"WorkingDesignSpec missing fields: {missing}"

    # Check that WorkingDesignSpec doesn't have extra core fields
    extra = working_core_fields - final_fields
    assert not extra, f"WorkingDesignSpec has unexpected core fields: {extra}"


def test_working_design_spec_incomplete():
    """Test that incomplete WorkingDesignSpec correctly identifies missing fields"""
    working = WorkingDesignSpec()

    assert not working.is_complete()
    missing = working.get_missing_fields()
    expected_missing = [
        "project_type",
        "dimensions",
        "fabric",
        "texture_preference",
        "complexity_preference",
    ]
    assert set(missing) == set(expected_missing)


def test_working_design_spec_complete():
    """Test that complete WorkingDesignSpec can convert to FinalDesignSpec"""
    # Create complete working spec
    working = WorkingDesignSpec(
        project_type=ProjectType.BLANKET,
        dimensions=Dimensions(width=50.0, length=60.0),
        fabric=FabricSpec(
            stitch_pattern=StitchPattern("Test", 2, 1, ["test"]),
            yarn_requirements=YarnSpec("worsted", "wool"),
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
        ),
        style_preferences={"texture": "simple", "complexity": "beginner"},
        special_requirements=[],
    )

    assert working.is_complete()
    assert working.get_missing_fields() == []

    # Should be able to convert to final spec
    final = working.to_final_design_spec()
    assert isinstance(final, DesignSpec)
    assert final.project_type == ProjectType.BLANKET
    assert final.dimensions.width == 50.0


def test_working_design_spec_conversion_fails_when_incomplete():
    """Test that incomplete WorkingDesignSpec raises error on conversion"""
    working = WorkingDesignSpec(
        project_type=ProjectType.BLANKET
        # Missing other required fields
    )

    with pytest.raises(ValueError) as exc_info:
        working.to_final_design_spec()

    assert "Cannot create FinalDesignSpec" in str(exc_info.value)
    assert "missing fields" in str(exc_info.value)


def test_conversation_state_basics():
    """Test basic conversation state functionality"""
    state = ConversationState()

    assert state.phase == ConversationPhase.INITIAL
    assert not state.working_spec.is_complete()
    assert state.should_ask_clarifying_questions()

    # Test message tracking
    state.add_user_message("I want a blanket")
    state.add_agent_message("What size would you like?")

    assert len(state.conversation_history) == 2
    assert state.conversation_history[0]["role"] == "user"
    assert state.conversation_history[1]["role"] == "agent"


def test_conversation_state_phase_advancement():
    """Test that conversation phases advance correctly"""
    state = ConversationState()

    assert state.phase == ConversationPhase.INITIAL

    state.advance_phase()
    assert state.phase == ConversationPhase.GATHERING_BASICS

    state.advance_phase()
    assert state.phase == ConversationPhase.EXPLORING_STYLE

    # Continue until complete
    while state.phase != ConversationPhase.COMPLETE:
        state.advance_phase()

    assert state.phase == ConversationPhase.COMPLETE

    # Should not advance beyond complete
    state.advance_phase()
    assert state.phase == ConversationPhase.COMPLETE


def test_conversation_summary():
    """Test conversation summary generation"""
    state = ConversationState()

    # Empty summary
    assert state.get_conversation_summary() == "No details gathered yet"

    # Add some details
    state.working_spec.project_type = ProjectType.BLANKET
    state.working_spec.dimensions = Dimensions(width=40.0, length=50.0)
    state.working_spec.style_preferences = {
        "texture": "cable",
        "complexity": "intermediate",
    }

    summary = state.get_conversation_summary()
    assert "Project: blanket" in summary
    assert 'Size: 40.0" x 50.0"' in summary
    assert "Style: texture: cable, complexity: intermediate" in summary
