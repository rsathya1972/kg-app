"""
File system utilities: safe path handling, MIME detection, file hashing.
"""
import hashlib
import mimetypes
import os
from pathlib import Path


# Supported MIME types for ingestion
SUPPORTED_MIME_TYPES: set[str] = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}

MIME_TO_EXTENSION: dict[str, str] = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}


def detect_mime_type(file_path: str | Path) -> str:
    """
    Detect MIME type of a file.
    Falls back to mimetypes.guess_type if python-magic is unavailable.
    """
    path = Path(file_path)
    try:
        import magic  # type: ignore
        return magic.from_file(str(path), mime=True)
    except ImportError:
        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"


def is_supported_file(file_path: str | Path) -> bool:
    """Return True if the file's MIME type is supported for ingestion."""
    return detect_mime_type(file_path) in SUPPORTED_MIME_TYPES


def file_sha256(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file for deduplication."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if it doesn't exist. Returns Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(name: str) -> str:
    """Strip unsafe characters from a filename."""
    return "".join(c for c in name if c.isalnum() or c in "._- ").strip()


def file_size_kb(file_path: str | Path) -> float:
    """Return file size in kilobytes."""
    return os.path.getsize(file_path) / 1024
