"""
Knowledge base module for the knitting pattern generation system.

This module provides the RAG (Retrieval-Augmented Generation) architecture
components including structured databases for patterns and yarns, and
unstructured knowledge for fabric principles.
"""

from .database import KnowledgeBaseDB
from .fabric_knowledge import FabricKnowledgeBase
from .schemas import DifficultyLevel, StitchPattern, YarnInfo, YarnWeight

__all__ = [
    "KnowledgeBaseDB",
    "StitchPattern",
    "YarnInfo",
    "DifficultyLevel",
    "YarnWeight",
    "FabricKnowledgeBase",
]
