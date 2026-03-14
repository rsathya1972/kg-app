# Utils Module

Shared utility functions used across all backend modules.

---

## Files

| File | Key Functions |
|------|--------------|
| `text_utils.py` | `count_tokens`, `truncate_to_tokens`, `normalize_whitespace`, `normalize_unicode`, `extract_sentences`, `word_count` |
| `async_utils.py` | `run_sync` — run blocking functions in executor |
| `file_utils.py` | `detect_mime_type`, `file_size_kb`, `is_supported_file` |
| `json_utils.py` | `strip_fences`, `safe_parse` — Claude JSON response helpers |

---

## Key Functions

### `run_sync(func)` — `async_utils.py`

Runs a synchronous blocking function in the asyncio thread pool executor. Required because the Anthropic Python SDK v0.40 is synchronous.

```python
from app.utils.async_utils import run_sync

# In an async route or service:
result = await run_sync(lambda: some_blocking_library_call(arg))
```

Use this for:
- Anthropic API calls (sync SDK)
- File I/O in async context
- Any CPU-bound or blocking operation inside `async def`

---

### `count_tokens(text, model)` — `text_utils.py`

Estimates token count. Uses `tiktoken` if installed, otherwise estimates at `0.75 tokens/char`.

```python
from app.utils.text_utils import count_tokens
n = count_tokens("some text", model="gpt-4")
```

---

### `truncate_to_tokens(text, max_tokens)` — `text_utils.py`

Truncates text to fit within a token budget. Used in `openai_client.py` before embedding calls.

---

### `detect_mime_type(path)` — `file_utils.py`

Returns MIME type string. Uses `python-magic` (byte-level detection) if available, falls back to `mimetypes` (extension-based).

```python
from app.utils.file_utils import detect_mime_type
mime = detect_mime_type("/path/to/file.pdf")  # → "application/pdf"
```

---

### `strip_fences(text)` — `json_utils.py`

Strips markdown code fences from Claude responses before JSON parsing.

```python
from app.utils.json_utils import strip_fences
clean = strip_fences("```json\n{\"key\": \"value\"}\n```")
# → '{"key": "value"}'
```

Always call this before `json.loads()` on Claude responses.

---

## Adding a New Utility

1. Add the function to the appropriate file (or create a new file for a new category)
2. Keep functions pure and stateless (no singleton state in utils)
3. Add docstring with arg types and return type
4. Test in `backend/tests/test_utils.py`
