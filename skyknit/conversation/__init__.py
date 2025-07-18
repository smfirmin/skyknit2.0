"""
Conversation infrastructure for interactive agents.

This module provides reusable conversation management components that can
be used by any agent that needs to have interactive dialogues with users.
"""

from .mixin import ConversationMixin
from .state import ConversationPhase, ConversationState, WorkingDesignSpec

__all__ = [
    "ConversationState",
    "ConversationPhase",
    "WorkingDesignSpec",
    "ConversationMixin",
]
