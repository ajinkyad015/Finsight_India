from __future__ import annotations

from typing import Any


UNSUPPORTED = "I couldn't verify this from the uploaded filings."


def validate_model_response(model_response: dict[str, Any], retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
    by_chunk = {chunk["chunk_id"]: chunk for chunk in retrieved_chunks}
    valid_citations: list[dict[str, Any]] = []
    for citation in model_response.get("citations", []):
        chunk_id = citation.get("chunk_id")
        if chunk_id in by_chunk:
            chunk = by_chunk[chunk_id]
            valid_citations.append(
                {
                    "document_id": chunk["document_id"],
                    "page_number": chunk["page_number"],
                    "chunk_id": chunk_id,
                }
            )

    answer = str(model_response.get("answer") or "").strip()
    unsupported = bool(model_response.get("unsupported")) or not answer or not valid_citations
    if unsupported:
        return {"answer": UNSUPPORTED, "citations": [], "unsupported": True}
    return {"answer": answer, "citations": valid_citations, "unsupported": False}
