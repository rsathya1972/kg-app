"""
Anthropic Claude API client placeholder.
Real implementation added in a later step once AI pipelines are defined.
"""
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class AnthropicClient:
    """Wrapper around the Anthropic SDK."""

    def __init__(self) -> None:
        self._api_key = settings.ANTHROPIC_API_KEY
        if not self._api_key:
            logger.warning("ANTHROPIC_API_KEY is not set — AI calls will fail")

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

        Raises:
            NotImplementedError: Until the real client is wired up.
        """
        raise NotImplementedError(
            "AnthropicClient.complete() is a placeholder. "
            "Install `anthropic` and implement in a later step."
        )


# Module-level singleton
anthropic_client = AnthropicClient()
