"""
Text cleaning: whitespace normalization, unicode normalization, noise removal.
"""
import re

from app.utils.text_utils import normalize_unicode, normalize_whitespace


class TextCleaner:
    """Cleans raw document text before chunking and AI processing."""

    def __init__(
        self,
        remove_urls: bool = False,
        remove_emails: bool = False,
        lowercase: bool = False,
    ) -> None:
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.lowercase = lowercase

    def clean(self, text: str) -> str:
        text = normalize_unicode(text)
        text = normalize_whitespace(text)

        if self.remove_urls:
            text = re.sub(r"https?://\S+", "", text)
        if self.remove_emails:
            text = re.sub(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", "", text)
        if self.lowercase:
            text = text.lower()

        # Remove repeated punctuation (e.g. "..." → "…" handled above; "---" → "—")
        text = re.sub(r"-{3,}", "—", text)
        text = re.sub(r"\.{3,}", "…", text)

        return text.strip()
