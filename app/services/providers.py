from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class ChatProvider(Protocol):
    async def answer_json(self, question: str, chunks: list[dict[str, Any]]) -> dict[str, Any]: ...


class MockEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([b / 255 for b in digest[:16]])
        return vectors


class MockChatProvider:
    async def answer_json(self, question: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not chunks:
            return {"answer": "I couldn't verify this from the uploaded filings.", "citations": [], "unsupported": True}
        first = chunks[0]
        return {
            "answer": f"Based on the uploaded filing excerpt, {first['text'][:240]}",
            "citations": [{"chunk_id": first["chunk_id"]}],
            "unsupported": False,
        }


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str, model: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


class OpenAIChatProvider:
    def __init__(self, api_key: str, model: str, system_prompt: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt

    async def answer_json(self, question: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": json.dumps({"question": question, "retrieved_chunks": chunks})},
            ],
        )
        return json.loads(response.choices[0].message.content or "{}")
