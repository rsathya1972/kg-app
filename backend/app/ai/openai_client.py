"""
OpenAI API client — completion and embedding support.
"""
import openai

from app.config import settings
from app.logger import get_logger
from app.utils.async_utils import run_sync

logger = get_logger(__name__)


class OpenAIClient:
    """Wrapper around the OpenAI SDK."""

    def __init__(self) -> None:
        self._api_key = settings.OPENAI_API_KEY
        if not self._api_key:
            logger.warning("OPENAI_API_KEY is not set — AI calls will fail")
        self._client = openai.OpenAI(api_key=self._api_key) if self._api_key else None

    async def complete(
        self,
        prompt: str,
        *,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> str:
        """
        Send a chat completion request to OpenAI.

        Returns:
            The assistant's response text.
        """
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        def _call() -> str:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        return await run_sync(_call)

    async def create_embedding(
        self,
        text: str,
        *,
        model: str = "text-embedding-3-small",
    ) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Input text to embed.
            model: OpenAI embedding model (default: text-embedding-3-small, 1536 dims).

        Returns:
            List of floats representing the embedding vector.
        """
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        # Truncate overly long inputs (safety guard — model limit is ~8191 tokens)
        safe_text = text[:32000] if len(text) > 32000 else text

        def _call() -> list[float]:
            response = self._client.embeddings.create(
                model=model,
                input=safe_text,
            )
            return response.data[0].embedding

        return await run_sync(_call)


# Module-level singleton
openai_client = OpenAIClient()
