import json
import logging
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.shared.exceptions import AIClientError

logger = logging.getLogger(__name__)


class AIClient:
    """Centralized Claude API wrapper with retry logic, structured outputs, and cost tracking."""

    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """Generate a text response from Claude."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            self._track_usage(response.usage)
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise AIClientError(f"Claude API call failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    )
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_choice: dict[str, str] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate a structured response using Claude's tool_use for typed outputs."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=tools,
                tool_choice=tool_choice or {"type": "any"},
            )
            self._track_usage(response.usage)

            # Extract the tool use result
            for block in response.content:
                if block.type == "tool_use":
                    return block.input
            raise AIClientError("No structured output returned from Claude")
        except anthropic.APIError as e:
            logger.error(f"Claude API structured output error: {e}")
            raise AIClientError(f"Claude structured output failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    )
    def classify(
        self,
        text: str,
        categories: list[str],
        context: str = "",
    ) -> str:
        """Classify text into one of the given categories."""
        system = "You are an expert document classifier. Respond with only the category name."
        prompt = f"""Classify the following text into exactly one of these categories: {', '.join(categories)}

{f'Context: {context}' if context else ''}

Text to classify:
{text[:3000]}

Category:"""
        result = self.generate(system, prompt, max_tokens=100)
        # Find the best matching category
        result_lower = result.strip().lower()
        for cat in categories:
            if cat.lower() in result_lower:
                return cat
        return categories[0]  # fallback to first category

    def _track_usage(self, usage):
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        logger.debug(
            f"Token usage - input: {usage.input_tokens}, output: {usage.output_tokens}, "
            f"total_input: {self.total_input_tokens}, total_output: {self.total_output_tokens}"
        )

    def get_usage_stats(self) -> dict[str, int]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }


# Singleton instance
_ai_client: AIClient | None = None


def get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
