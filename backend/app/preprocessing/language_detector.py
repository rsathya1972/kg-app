"""
Language detection: wraps langdetect with a graceful fallback.
"""
from app.logger import get_logger

logger = get_logger(__name__)


def detect_language(text: str) -> str | None:
    """
    Detect the language of the given text.

    Returns:
        ISO 639-1 language code (e.g. "en", "de", "fr") or None if detection fails.

    Requires:
        langdetect — install with: pip install langdetect
    """
    if not text or len(text.split()) < 5:
        return None

    try:
        from langdetect import detect, LangDetectException  # type: ignore
        code = detect(text[:2000])  # Use first 2000 chars for speed
        logger.debug("Detected language: %s", code)
        return code
    except ImportError:
        logger.debug("langdetect not installed — language detection skipped")
        return None
    except Exception as exc:
        logger.warning("Language detection failed: %s", exc)
        return None
