"""Evaluate retrieval quality on a labeled question set, scoped to one document.

Same measurement philosophy as the original repo: page recall@k + a reranker ablation
(rerank ON vs OFF) to prove the Cohere rerank step earns its extra API call.
"""
from __future__ import annotations

import argparse

import yaml

from .index import HybridIndex
from .retrieve import retrieve


def _page_hit(chunks, expected_pages) -> bool:
    got = {c["page"] for c in chunks}
    return any(p in got for p in expected_pages)


def _keyword_grounding(chunks, keywords) -> float:
    blob = " ".join(c["text"].lower() for c in chunks)
    if not keywords:
        return 1.0
    return sum(1 for k in keywords if k.lower() in blob) / len(keywords)


def evaluate(questions_path: str, doc_id: str | None, top_k: int = 5) -> dict:
    qs = yaml.safe_load(open(questions_path))["questions"]
    index = HybridIndex()
    doc_ids = [doc_id] if doc_id else None

    rows = []
    for q in qs:
        on = retrieve(index, q["question"], top_k, rerank=True, doc_ids=doc_ids)
        off = retrieve(index, q["question"], top_k, rerank=False, doc_ids=doc_ids)
        rows.append({
            "question": q["question"],
            "hit_rerank": _page_hit(on, q.get("expected_pages", [])),
            "hit_fused": _page_hit(off, q.get("expected_pages", [])),
            "grounding": _keyword_grounding(on, q.get("expected_keywords", [])),
        })

    n = len(rows)
    summary = {
        "n_questions": n,
        "page_recall@k_reranked": sum(r["hit_rerank"] for r in rows) / n,
        "page_recall@k_fused": sum(r["hit_fused"] for r in rows) / n,
        "keyword_grounding": sum(r["grounding"] for r in rows) / n,
    }
    return {"summary": summary, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="evaluate retrieval + grounding")
    ap.add_argument("--questions", default="eval/questions.yaml")
    ap.add_argument("--doc-id", default=None, help="scope eval to one uploaded doc_id")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    res = evaluate(args.questions, args.doc_id, args.top_k)
    s = res["summary"]
    print(f"\nquestions             : {s['n_questions']}")
    print(f"page recall@{args.top_k} (rerank): {s['page_recall@k_reranked']:.3f}")
    print(f"page recall@{args.top_k} (fused) : {s['page_recall@k_fused']:.3f}  "
          f"(rerank lift: {s['page_recall@k_reranked'] - s['page_recall@k_fused']:+.3f})")
    print(f"keyword grounding     : {s['keyword_grounding']:.3f}")


if __name__ == "__main__":
    main()
