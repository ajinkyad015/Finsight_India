"""Chunk extracted pages into overlapping word windows, scoped per page.

Chunks never straddle a page boundary — same rationale as the original section-aware
design: keeps citations clean ("p. 12" always means exactly p. 12) and stops content
from one page bleeding into another chunk's context.
"""
from __future__ import annotations


def chunk_words(text: str, size: int = 220, overlap: int = 40) -> list[str]:
    """Sliding word-window chunks. Overlap preserves context across the cut."""
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)] if words else []
    step = max(1, size - overlap)
    out = []
    for start in range(0, len(words), step):
        window = words[start:start + size]
        out.append(" ".join(window))
        if start + size >= len(words):
            break
    return out


def chunk_document(
    doc_id: str, company: str, year: str, pages: list[dict],
    size: int = 220, overlap: int = 40,
) -> list[dict]:
    """pages: [{"page": int, "text": str}, ...] -> chunk records ready to embed/index."""
    chunks = []
    for p in pages:
        for j, body in enumerate(chunk_words(p["text"], size, overlap)):
            chunks.append({
                "id": f"{doc_id}:p{p['page']}:{j}",
                "doc_id": doc_id,
                "company": company,
                "year": year,
                "page": p["page"],
                "text": body,
            })
    return chunks
