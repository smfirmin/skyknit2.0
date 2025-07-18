"""
Ollama local model client implementation for knitting pattern generation.
"""

import json
import logging

from .base_client import BaseLLMClient, LLMConfig

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """Ollama local model client implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.model = config.model or "llama3.2:3b"

        # Test connection to Ollama
        self._test_connection()

    def _test_connection(self):
        """Test if Ollama is running and accessible"""
        import requests

        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(
                    f"Ollama server returned status {response.status_code}"
                )

            # Check if our model is available
            models = response.json().get("models", [])
            model_names = [model.get("name", "") for model in models]

            if not any(self.model in name for name in model_names):
                logger.warning(
                    f"Model {self.model} not found in Ollama. Available models: {model_names}"
                )

        except requests.exceptions.RequestException as err:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}: {err}"
            ) from err

    def generate(self, messages, **kwargs) -> str:
        """Generate text using Ollama"""
        import requests

        # Convert messages to a single prompt
        prompt = self._messages_to_prompt(messages)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def generate_structured(self, messages, schema, **kwargs):
        """Generate structured output using Ollama"""
        # Add JSON schema instruction to the prompt
        schema_instruction = f"\n\nPlease respond with valid JSON matching this exact schema: {json.dumps(schema)}"

        # Modify the last user message
        modified_messages = messages.copy()
        for i in range(len(modified_messages) - 1, -1, -1):
            if modified_messages[i]["role"] == "user":
                modified_messages[i]["content"] += schema_instruction
                break

        response_text = self.generate(modified_messages, **kwargs)

        try:
            # Extract JSON from response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Ollama structured response: {e}")
            logger.error(f"Response text: {response_text}")
            raise

    def _messages_to_prompt(self, messages) -> str:
        """Convert chat messages to a single prompt for Ollama"""
        prompt_parts = []

        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
