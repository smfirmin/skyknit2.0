"""
LLM integration module for the knitting pattern generation system.

This module provides LLM-powered agents that use RAG (Retrieval-Augmented Generation)
to combine structured knowledge base data with unstructured fabric principles.
"""

from .anthropic_client import AnthropicClient
from .base_client import BaseLLMClient, LLMConfig, load_credentials
from .ollama_client import OllamaClient


class LLMClient:
    """Main LLM client factory"""

    @staticmethod
    def create(config: LLMConfig) -> BaseLLMClient:
        """Create an LLM client based on configuration"""
        if config.provider == "anthropic":
            return AnthropicClient(config)
        elif config.provider == "ollama":
            return OllamaClient(config)
        else:
            raise ValueError(
                f"Unsupported LLM provider: {config.provider}. Supported providers: anthropic, ollama"
            )

    @staticmethod
    def create_anthropic(credentials_path: str = "credentials.json") -> BaseLLMClient:
        """Create Anthropic client with credentials from file"""
        credentials = load_credentials(credentials_path)
        api_key = credentials.get("anthropic", {}).get("api_key")

        if not api_key:
            raise ValueError("Anthropic API key not found in credentials file")

        config = LLMConfig(
            provider="anthropic", model="claude-3-haiku-20240307", api_key=api_key
        )
        return AnthropicClient(config)

    @staticmethod
    def create_ollama(credentials_path: str = "credentials.json") -> BaseLLMClient:
        """Create Ollama client with configuration from file"""
        credentials = load_credentials(credentials_path)
        ollama_config = credentials.get("ollama", {})

        # Use defaults if not specified
        base_url = ollama_config.get("base_url", "http://localhost:11434")
        model = ollama_config.get("model", "gemma3:4b")

        config = LLMConfig(provider="ollama", model=model, base_url=base_url)
        return OllamaClient(config)


__all__ = [
    "BaseLLMClient",
    "LLMConfig",
    "LLMClient",
    "AnthropicClient",
    "OllamaClient",
    "load_credentials",
]
