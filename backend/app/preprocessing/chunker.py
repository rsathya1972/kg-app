"""
Text chunking: sliding window and sentence-based strategies.
"""
from app.config import settings
from app.preprocessing.base import TextChunk
from app.utils.text_utils import count_tokens, extract_sentences


class SlidingWindowChunker:
    """
    Splits text into overlapping chunks of approximately max_tokens tokens.
    Uses word boundaries to avoid splitting mid-sentence where possible.
    """

    def __init__(
        self,
        max_tokens: int | None = None,
        overlap_tokens: int | None = None,
    ) -> None:
        self.max_tokens = max_tokens or settings.MAX_CHUNK_SIZE
        self.overlap_tokens = overlap_tokens or settings.CHUNK_OVERLAP

    def chunk(self, text: str) -> list[TextChunk]:
        words = text.split()
        if not words:
            return []

        chunks: list[TextChunk] = []
        step = max(1, self.max_tokens - self.overlap_tokens)
        # Estimate: 1 word ≈ 1.3 tokens on average
        words_per_chunk = int(self.max_tokens / 1.3)
        words_step = int(step / 1.3)

        start_word = 0
        chunk_index = 0
        char_offset = 0

        while start_word < len(words):
            end_word = min(start_word + words_per_chunk, len(words))
            chunk_text = " ".join(words[start_word:end_word])
            start_char = text.find(chunk_text, char_offset)
            end_char = start_char + len(chunk_text) if start_char >= 0 else -1

            chunks.append(TextChunk(
                index=chunk_index,
                text=chunk_text,
                start_char=max(0, start_char),
                end_char=max(0, end_char),
                token_count=count_tokens(chunk_text),
            ))

            start_word += words_step
            char_offset = max(0, start_char)
            chunk_index += 1

        return chunks


class SentenceChunker:
    """
    Splits text into chunks at sentence boundaries, grouping sentences until
    the token budget is reached.
    """

    def __init__(self, max_tokens: int | None = None) -> None:
        self.max_tokens = max_tokens or settings.MAX_CHUNK_SIZE

    def chunk(self, text: str) -> list[TextChunk]:
        sentences = extract_sentences(text)
        if not sentences:
            return []

        chunks: list[TextChunk] = []
        current_sentences: list[str] = []
        current_tokens = 0
        chunk_index = 0
        char_pos = 0

        for sentence in sentences:
            sent_tokens = count_tokens(sentence)
            if current_sentences and current_tokens + sent_tokens > self.max_tokens:
                chunk_text = " ".join(current_sentences)
                start_char = text.find(chunk_text, char_pos)
                chunks.append(TextChunk(
                    index=chunk_index,
                    text=chunk_text,
                    start_char=max(0, start_char),
                    end_char=max(0, start_char + len(chunk_text)),
                    token_count=current_tokens,
                ))
                char_pos = max(0, start_char + len(chunk_text))
                chunk_index += 1
                current_sentences = []
                current_tokens = 0

            current_sentences.append(sentence)
            current_tokens += sent_tokens

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            start_char = text.find(chunk_text, char_pos)
            chunks.append(TextChunk(
                index=chunk_index,
                text=chunk_text,
                start_char=max(0, start_char),
                end_char=max(0, start_char + len(chunk_text)),
                token_count=current_tokens,
            ))

        return chunks
