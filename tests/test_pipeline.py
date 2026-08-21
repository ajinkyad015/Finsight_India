"""Unit tests for the key-free parts: chunking, RRF fusion, document chunking."""
from src.chunk import chunk_document, chunk_words
from src.retrieve import _rrf


def test_chunk_overlap_and_coverage():
    words = " ".join(str(i) for i in range(500))
    chunks = chunk_words(words, size=100, overlap=20)
    assert len(chunks) >= 5
    c0_tail = chunks[0].split()[-20:]
    c1_head = chunks[1].split()[:20]
    assert c0_tail == c1_head


def test_chunk_short_text_single_chunk():
    assert chunk_words("a b c", size=100) == ["a b c"]
    assert chunk_words("", size=100) == []


def test_rrf_rewards_agreement():
    fused = _rrf([[2, 0, 1], [2, 1, 0]])
    assert max(fused, key=fused.get) == 2


def test_chunk_document_never_crosses_pages():
    pages = [{"page": 1, "text": "alpha " * 300}, {"page": 2, "text": "beta " * 10}]
    chunks = chunk_document("DOC1", "Acme Ltd", "2024", pages, size=100, overlap=20)
    assert all(c["doc_id"] == "DOC1" for c in chunks)
    # page-1 chunks only contain "alpha", page-2 chunk only contains "beta"
    for c in chunks:
        if c["page"] == 1:
            assert "beta" not in c["text"]
        else:
            assert "alpha" not in c["text"]
