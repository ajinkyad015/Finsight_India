"""Grounded answer generation with Gemini, with inline [n] citations to retrieved chunks.

Same grounding contract as the original repo — the prompt design is model-agnostic,
only the client call changed. Falls back to an extractive answer if GEMINI_API_KEY is
unset, so retrieval/eval can still be exercised without a key.
"""
from __future__ import annotations

import os

MODEL = os.getenv("ANSWER_MODEL", "gemini-2.0-flash")

SYSTEM = (
    "You are a financial-filings analyst reviewing Indian company annual reports. Answer "
    "the user's question using ONLY the numbered context passages below. Cite every "
    "factual claim with the passage number in square brackets, e.g. [1] or [2][3]. If the "
    "passages do not contain the answer, say so plainly, do not use outside knowledge or "
    "guess. Be concise and quantitative where the filing is (cite figures in Rs./crore as "
    "given, don't convert units)."
)


def format_context(chunks: list[dict]) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"[{i}] ({c['company']} FY{c['year']}, p.{c['page']}) {c['text']}")
    return "\n\n".join(lines)


def answer(question: str, chunks: list[dict], max_tokens: int = 1024) -> dict:
    """Return {answer, citations, model, grounded}. Falls back to extractive without a key."""
    context = format_context(chunks)
    sources = [
        {"n": i + 1, "id": c["id"], "company": c["company"], "year": c["year"], "page": c["page"]}
        for i, c in enumerate(chunks)
    ]

    if not os.getenv("GEMINI_API_KEY"):
        extractive = "\n\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks[:3]))
        return {
            "answer": "(no GEMINI_API_KEY — returning top retrieved passages verbatim)\n\n" + extractive,
            "citations": sources, "model": "extractive-fallback", "grounded": True,
        }

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=MODEL,
        contents=f"Question: {question}\n\nContext:\n{context}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM, max_output_tokens=max_tokens,
        ),
    )
    return {"answer": resp.text, "citations": sources, "model": MODEL, "grounded": True}
