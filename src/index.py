"""Build/load a single GLOBAL hybrid index spanning every uploaded report.

Rather than one index per document, all chunks live in one BM25 + FAISS index tagged
with doc_id/company/year. This lets a query span multiple companies naturally (e.g.
"compare revenue growth across these two reports") and keeps the architecture simple —
at demo scale (a handful of annual reports, a few thousand chunks) rebuilding both
indexes on every upload/delete is trivial CPU work, so we don't bother with incremental
updates.

Persisted under STORE_DIR (see storage.py), optionally synced to GCS:
    documents.json   uploaded-report metadata (doc_id, company, year, filename, n_chunks)
    chunks.jsonl     every chunk across every document
    bm25.pkl         pickled rank_bm25 model over the full corpus
    dense.faiss      FAISS inner-product index over normalized Gemini embeddings
"""
from __future__ import annotations

import json
import pickle
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import storage
from .chunk import chunk_document
from .embed import embed_passages, embed_query

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _paths():
    d = storage.STORE_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d / "documents.json", d / "chunks.jsonl", d / "bm25.pkl", d / "dense.faiss"


def _load_chunks(chunks_path: Path) -> list[dict]:
    if not chunks_path.exists():
        return []
    return [json.loads(l) for l in chunks_path.read_text().splitlines() if l]


def _load_documents(docs_path: Path) -> list[dict]:
    if not docs_path.exists():
        return []
    return json.loads(docs_path.read_text())


def _rebuild(chunks: list[dict], bm25_path: Path, faiss_path: Path) -> None:
    """Rebuild BM25 + FAISS from the current full chunk list. Skips embedding if no chunks."""
    from rank_bm25 import BM25Okapi

    corpus = [tokenize(c["text"]) for c in chunks]
    with open(bm25_path, "wb") as f:
        pickle.dump({"bm25": BM25Okapi(corpus) if corpus else None}, f)

    import faiss

    if not chunks:
        faiss.write_index(faiss.IndexFlatIP(768), str(faiss_path))  # empty placeholder
        return
    vecs = np.asarray(embed_passages([c["text"] for c in chunks]), dtype="float32")
    faiss_index = faiss.IndexFlatIP(vecs.shape[1])
    faiss_index.add(vecs)
    faiss.write_index(faiss_index, str(faiss_path))


def add_document(doc_id: str, company: str, year: str, filename: str, pages: list[dict]) -> dict:
    """Chunk + embed a newly-uploaded report, append to the global corpus, rebuild, persist."""
    docs_path, chunks_path, bm25_path, faiss_path = _paths()
    storage.download()  # pull latest state before mutating, in case of multi-instance drift

    existing_chunks = _load_chunks(chunks_path)
    new_chunks = chunk_document(doc_id, company, year, pages)
    all_chunks = existing_chunks + new_chunks

    chunks_path.write_text("\n".join(json.dumps(c) for c in all_chunks))
    _rebuild(all_chunks, bm25_path, faiss_path)

    docs = _load_documents(docs_path)
    meta = {
        "doc_id": doc_id, "company": company, "year": year, "filename": filename,
        "n_chunks": len(new_chunks),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    docs.append(meta)
    docs_path.write_text(json.dumps(docs, indent=2))

    storage.upload()
    return meta


def remove_document(doc_id: str) -> None:
    docs_path, chunks_path, bm25_path, faiss_path = _paths()
    storage.download()

    chunks = [c for c in _load_chunks(chunks_path) if c["doc_id"] != doc_id]
    chunks_path.write_text("\n".join(json.dumps(c) for c in chunks))
    _rebuild(chunks, bm25_path, faiss_path)

    docs = [d for d in _load_documents(docs_path) if d["doc_id"] != doc_id]
    docs_path.write_text(json.dumps(docs, indent=2))

    storage.upload()


def list_documents() -> list[dict]:
    docs_path, _, _, _ = _paths()
    storage.download()
    return _load_documents(docs_path)


class HybridIndex:
    """Loaded global index exposing lexical + dense search, filterable by doc_id."""

    def __init__(self):
        import faiss

        storage.download()
        docs_path, chunks_path, bm25_path, faiss_path = _paths()
        self.chunks: list[dict] = _load_chunks(chunks_path)
        if bm25_path.exists():
            with open(bm25_path, "rb") as f:
                self.bm25 = pickle.load(f)["bm25"]
        else:
            self.bm25 = None
        self.dense = faiss.read_index(str(faiss_path)) if faiss_path.exists() else None

    def bm25_scores(self, query: str) -> np.ndarray:
        if self.bm25 is None or not self.chunks:
            return np.zeros(len(self.chunks))
        return np.asarray(self.bm25.get_scores(tokenize(query)))

    def dense_search(self, query: str, k: int) -> list[tuple[int, float]]:
        if self.dense is None or self.dense.ntotal == 0:
            return []
        q = np.asarray([embed_query(query)], dtype="float32")
        scores, idx = self.dense.search(q, min(k, self.dense.ntotal))
        return list(zip(idx[0].tolist(), scores[0].tolist()))
