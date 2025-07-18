"""
Anthropic Claude client implementation for knitting pattern generation.
"""

import json
import logging

from .base_client import BaseLLMClient, LLMConfig

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=config.api_key)
        except ImportError as err:
            raise ImportError(
                "Anthropic package not installed. Run: pip install anthropic"
            ) from err

    def generate(self, messages, **kwargs) -> str:
        """Generate text using Anthropic Claude"""

        try:
            # Convert messages to Anthropic format
            system_message = ""
            user_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)

            response = self.client.messages.create(
                model=self.config.model,
                system=system_message,
                messages=user_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout,
                **kwargs,
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def generate_structured(self, messages, schema, **kwargs):
        """Generate structured output using Anthropic"""
        # Add JSON schema instruction to the last user message
        schema_instruction = f"\n\nPlease respond with valid JSON matching this schema: {json.dumps(schema)}"

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
            logger.error(f"Failed to parse structured response: {e}")
            logger.error(f"Response text: {response_text}")
            raise
