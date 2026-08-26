"""Embeddings via the Gemini API — no model is ever loaded into this process.

Centralized so index-build (passages) and query-time (query) embedding stay consistent.
Batches passage embedding calls to stay well within free-tier request limits.
"""
from __future__ import annotations

import os

_MODEL = os.getenv("EMBED_MODEL", "models/gemini-embedding-2")
_BATCH = 100  # Gemini batch_embed_contents cap per call
_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed corpus passages, task-typed for retrieval (asymmetric doc/query embeddings)."""
    from google.genai import types

    client = _get_client()
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i:i + _BATCH]
        resp = client.models.embed_content(
            model=_MODEL, contents=batch,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        out.extend(e.values for e in resp.embeddings)
    return out

from google.genai import types

def embed_query(text: str) -> list[float]:
    
    client = _get_client()
    resp = client.models.embed_content(
        model=_MODEL, contents=[text],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return resp.embeddings[0].values
