# Preprocessing Module

Cleans raw document text and splits it into chunks for AI processing and embedding.

---

## Files

| File | Purpose |
|------|---------|
| `base.py` | `TextChunk`, `PreprocessedDocument`, `BasePreprocessor` ABC |
| `chunker.py` | `SlidingWindowChunker`, `SentenceChunker` |
| `text_cleaner.py` | Stub — text normalization |
| `language_detector.py` | Stub — language detection |

---

## Key Classes

### `SlidingWindowChunker`

Splits text into overlapping windows by estimated token count.

```python
from app.preprocessing.chunker import SlidingWindowChunker

chunker = SlidingWindowChunker(
    chunk_size=600,    # tokens per chunk (default from settings: 1000)
    overlap=50         # overlap tokens between chunks (default: 100)
)
chunks: list[TextChunk] = chunker.chunk(text)
# chunks[0].text: chunk text
# chunks[0].index: 0-based position
# chunks[0].token_count: estimated token count
# chunks[0].start_char / end_char: character offsets in original text
```

Token estimation: `1 word ≈ 1.3 tokens` (conservative estimate; no tokenizer dependency required).

### `SentenceChunker`

Groups sentences until the token budget is reached. Produces more linguistically meaningful boundaries at the cost of potentially smaller/variable chunk sizes.

```python
from app.preprocessing.chunker import SentenceChunker

chunker = SentenceChunker(max_tokens=1000)
chunks = chunker.chunk(text)
```

Sentence splitting uses regex in `backend/app/utils/text_utils.py` `extract_sentences()`.

---

## TextChunk

```python
@dataclass
class TextChunk:
    index: int
    text: str
    start_char: int
    end_char: int
    token_count: int
    metadata: dict     # e.g. {"source_page": 3}
```

---

## Which Chunker Is Used Where

| Consumer | Chunker | chunk_size | overlap |
|----------|---------|------------|---------|
| Entity extraction | `SlidingWindowChunker` | 600 | 50 |
| Relationship extraction | `SlidingWindowChunker` | 600 | 50 |
| Vector embeddings | `SlidingWindowChunker` | settings.MAX_CHUNK_SIZE | settings.CHUNK_OVERLAP |

Extraction uses smaller chunks (600 tokens) to keep Claude prompts focused. Embedding uses the configurable `MAX_CHUNK_SIZE` (default 1000) for richer context per search result.

---

## How to Add a New Chunker

1. Subclass `BasePreprocessor` from `base.py` and implement `chunk(text) → list[TextChunk]`
2. Add to `chunker.py`
3. Write tests in `backend/tests/test_chunker.py`
4. Update the consumer (extraction or embedding service) to use the new chunker
