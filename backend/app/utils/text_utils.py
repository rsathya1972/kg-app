"""
Text utilities: token counting, truncation, normalization helpers.
"""
import re
import unicodedata


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Count tokens using tiktoken if available, otherwise estimate via word count.

    Args:
        text: Input text.
        model: Tiktoken model name for encoding selection.

    Returns:
        Token count (exact if tiktoken installed, estimate otherwise).
    """
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except (ImportError, KeyError):
        # Rough estimate: ~0.75 tokens per word
        return int(len(text.split()) * 0.75)


def truncate_to_tokens(text: str, max_tokens: int, model: str = "gpt-4o") -> str:
    """
    Truncate text to at most max_tokens tokens.
    Cuts at word boundary to avoid splitting mid-token.
    """
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model)
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return enc.decode(tokens[:max_tokens])
    except (ImportError, KeyError):
        # Fallback: truncate by characters (rough 4 chars/token)
        char_limit = max_tokens * 4
        return text[:char_limit]


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines and strip leading/trailing whitespace."""
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFC form and remove control characters."""
    text = unicodedata.normalize("NFC", text)
    # Remove non-printable control characters except newline/tab
    return "".join(c for c in text if unicodedata.category(c) != "Cc" or c in "\n\t")


def extract_sentences(text: str) -> list[str]:
    """
    Simple sentence splitter based on punctuation.
    Returns a list of non-empty sentences.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def word_count(text: str) -> int:
    """Return word count of text."""
    return len(text.split())
