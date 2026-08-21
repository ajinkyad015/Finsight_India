"""Hybrid retrieval: BM25 + dense, fused with Reciprocal Rank Fusion, then Cohere-reranked.

Same staged design as the original repo so each stage's contribution stays measurable:
  1. BM25 top-N   (lexical recall) — scored globally, then masked to selected doc_ids
  2. dense top-N  (semantic recall) — over-fetched, then filtered to selected doc_ids
  3. RRF fusion   (rank-based merge)
  4. Cohere rerank of the fused candidates (precision) — API call, no local model

`rerank=False` returns the fused list, so the eval can isolate the reranker's lift,
exactly as before.
"""
from __future__ import annotations

import os

from .index import HybridIndex

_cohere_client = None


def _rrf(rank_lists: list[list[int]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for rank, idx in enumerate(ranks):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank)
    return scores


def _get_cohere():
    global _cohere_client
    if _cohere_client is None:
        import cohere

        _cohere_client = cohere.Client(os.environ["COHERE_API_KEY"])
    return _cohere_client


def retrieve(
    index: HybridIndex,
    query: str,
    top_k: int = 5,
    candidates: int = 20,
    rerank: bool = True,
    doc_ids: list[str] | None = None,
) -> list[dict]:
    """Return up to top_k chunk dicts with a `score` and `stage`, optionally scoped to doc_ids."""
    n = len(index.chunks)
    if n == 0:
        return []

    allowed = None
    if doc_ids:
        allowed = {i for i, c in enumerate(index.chunks) if c["doc_id"] in doc_ids}
        if not allowed:
            return []

    # over-fetch generously when filtering, since many candidates may get masked out
    fetch = min(candidates * 5, n) if allowed else min(candidates, n)

    bm25 = index.bm25_scores(query)
    bm25_rank = [i for i in bm25.argsort()[::-1] if allowed is None or i in allowed][:candidates]

    dense_hits = index.dense_search(query, fetch)
    dense_rank = [i for i, _ in dense_hits if allowed is None or i in allowed][:candidates]

    fused = _rrf([bm25_rank, dense_rank])
    fused_ids = sorted(fused, key=fused.get, reverse=True)[:candidates]

    if not fused_ids:
        return []

    if not rerank:
        return [{**index.chunks[i], "score": fused[i], "stage": "fused"} for i in fused_ids[:top_k]]

    docs = [index.chunks[i]["text"] for i in fused_ids]
    resp = _get_cohere().rerank(
        model=os.getenv("RERANK_MODEL", "rerank-english-v3.0"),
        query=query, documents=docs, top_n=min(top_k, len(docs)),
    )
    return [
        {**index.chunks[fused_ids[r.index]], "score": float(r.relevance_score), "stage": "reranked"}
        for r in resp.results
    ]
