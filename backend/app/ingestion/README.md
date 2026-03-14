# Ingestion Module

Reads raw content from files (TXT, PDF, DOCX) or plain text and returns a normalised `IngestedDocument`.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | `IngestedDocument` dataclass, `BaseIngester` ABC |
| `file_ingester.py` | `FileIngester` — handles TXT/PDF/DOCX files |
| `registry.py` | `IngesterRegistry` — dispatches to correct ingester by source type |

---

## Supported Source Types

| Source type | Handler | Library |
|-------------|---------|---------|
| `file` (TXT) | `FileIngester` | Built-in `open()` |
| `file` (PDF) | `FileIngester` | `pypdf` |
| `file` (DOCX) | `FileIngester` | `python-docx` |
| `text` | (inline) | No file I/O |
| `url` | Stub | Not implemented — raises `NotImplementedError` |

---

## Key Class

### `FileIngester`

```python
ingester = FileIngester()
doc: IngestedDocument = await ingester.ingest(
    source="/path/to/file.pdf",
    metadata={"uploaded_by": "user"}
)
# doc.raw_text: extracted text
# doc.mime_type: detected MIME type
# doc.word_count: computed word count
```

### `IngestedDocument`

```python
@dataclass
class IngestedDocument:
    id: str               # UUID (generated)
    source_type: str      # "file" | "text" | "url"
    raw_text: str         # Full extracted text
    filename: str
    mime_type: str        # e.g. "application/pdf"
    source_url: str | None
    size_kb: float
    language: str         # Detected language code (stub → "en")
    metadata: dict
    ingested_at: datetime
```

---

## How to Add a New File Format

1. Add the MIME type to `file_ingester.py`'s dispatch table
2. Implement extraction using the appropriate library
3. Add the new MIME type to `backend/app/utils/file_utils.py` `SUPPORTED_TYPES`
4. Add a fixture file to `backend/tests/fixtures/` and write a test

---

## MIME Type Detection

Uses `python-magic` if available (byte-level MIME sniffing), falls back to `mimetypes` (extension-based). Handled in `backend/app/utils/file_utils.py` `detect_mime_type(path)`.
