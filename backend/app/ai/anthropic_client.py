"""
Anthropic Claude API client.
"""
import anthropic

from app.config import settings
from app.logger import get_logger
from app.utils.async_utils import run_sync

logger = get_logger(__name__)


class AnthropicClient:
    """Wrapper around the Anthropic SDK."""

    def __init__(self) -> None:
        self._api_key = settings.ANTHROPIC_API_KEY
        if not self._api_key:
            logger.warning("ANTHROPIC_API_KEY is not set — AI calls will fail")
        self._client = anthropic.Anthropic(api_key=self._api_key)

    async def complete(
        self,
        prompt: str,
        *,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> str:
        """
        Send a completion request to Claude.

        Args:
            prompt: User message text.
            model: Claude model ID.
            max_tokens: Maximum tokens in the response.
            system: Optional system prompt.

        Returns:
            The assistant's response text.
        """
        def _call() -> str:
            kwargs: dict = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            response = self._client.messages.create(**kwargs)
            return response.content[0].text

        logger.debug("Claude request model=%s max_tokens=%d", model, max_tokens)
        result = await run_sync(_call)
        logger.debug("Claude response length=%d chars", len(result))
        return result


# Module-level singleton
anthropic_client = AnthropicClient()
