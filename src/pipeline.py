"""End-to-end: PDF upload -> extract+chunk+embed+index, and question -> retrieve+rerank+answer."""
from __future__ import annotations

import uuid

from .extract import extract_pages
from .generate import answer as generate_answer
from .index import HybridIndex, add_document, list_documents, remove_document
from .retrieve import retrieve


class RAGPipeline:
    def __init__(self, top_k: int = 5, candidates: int = 20, rerank: bool = True):
        self.top_k = top_k
        self.candidates = candidates
        self.rerank = rerank

    def ingest(self, pdf_path: str, company: str, year: str, filename: str) -> dict:
        pages = extract_pages(pdf_path)
        doc_id = f"{company.strip().upper().replace(' ', '_')}_{year}_{uuid.uuid4().hex[:6]}"
        return add_document(doc_id, company.strip(), str(year), filename, pages)

    def documents(self) -> list[dict]:
        return list_documents()

    def delete(self, doc_id: str) -> None:
        remove_document(doc_id)

    def ask(
        self, question: str, doc_ids: list[str] | None = None,
        top_k: int | None = None, rerank: bool | None = None,
    ) -> dict:
        index = HybridIndex()  # reload each call — cheap at demo scale, always fresh after ingest
        chunks = retrieve(
            index, question,
            top_k if top_k is not None else self.top_k,
            self.candidates,
            rerank if rerank is not None else self.rerank,
            doc_ids,
        )
        if not chunks:
            return {
                "answer": "No matching content found — upload a report or broaden your selection.",
                "citations": [], "model": "n/a", "grounded": True, "retrieved": [],
            }
        result = generate_answer(question, chunks)
        result["retrieved"] = [
            {"id": c["id"], "company": c["company"], "year": c["year"], "page": c["page"],
             "score": round(c["score"], 4)} for c in chunks
        ]
        return result
