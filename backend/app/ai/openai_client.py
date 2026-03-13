"""
OpenAI API client placeholder.
Real implementation added in a later step once AI pipelines are defined.
"""
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """Wrapper around the OpenAI SDK."""

    def __init__(self) -> None:
        self._api_key = settings.OPENAI_API_KEY
        if not self._api_key:
            logger.warning("OPENAI_API_KEY is not set — AI calls will fail")

    async def complete(
        self,
        prompt: str,
        *,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> str:
        """
        Send a completion request to OpenAI.

        Args:
            prompt: User message text.
            model: OpenAI model ID.
            max_tokens: Maximum tokens in the response.
            system: Optional system prompt.

        Returns:
            The assistant's response text.

        Raises:
            NotImplementedError: Until the real client is wired up.
        """
        raise NotImplementedError(
            "OpenAIClient.complete() is a placeholder. "
            "Install `openai` and implement in a later step."
        )


# Module-level singleton
openai_client = OpenAIClient()
