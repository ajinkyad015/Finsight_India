from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    page_number: int
    text: str
    context: str


def chunk_pages(document_id: str, pages: list[tuple[int, str]], size: int = 900, overlap: int = 120) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page_number, text in pages:
        words = text.split()
        if not words:
            continue
        start = 0
        part = 0
        while start < len(words):
            end = min(len(words), start + size)
            chunk_text = " ".join(words[start:end])
            context_start = max(0, start - 30)
            context_end = min(len(words), end + 30)
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}:p{page_number}:c{part}",
                    page_number=page_number,
                    text=chunk_text,
                    context=" ".join(words[context_start:context_end]),
                )
            )
            if end == len(words):
                break
            start = max(end - overlap, start + 1)
            part += 1
    return chunks
