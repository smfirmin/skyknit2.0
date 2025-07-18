"""
Base LLM client interface for knitting pattern generation.

This module provides the abstract base class and configuration for LLM providers.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def load_credentials(credentials_path: str = "credentials.json") -> dict[str, Any]:
    """Load credentials from local file"""
    try:
        with open(credentials_path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Credentials file {credentials_path} not found")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in credentials file {credentials_path}")
        return {}


@dataclass
class LLMConfig:
    """Configuration for LLM client"""

    provider: str  # "anthropic", "ollama"
    model: str = "claude-3-haiku-20240307"
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 1000
    temperature: float = 0.1  # Low temperature for consistent knitting advice
    timeout: int = 30


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Generate text from messages"""
        pass

    @abstractmethod
    def generate_structured(
        self, messages: list[dict[str, str]], schema: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        """Generate structured output matching a schema"""
        pass
