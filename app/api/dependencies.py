from __future__ import annotations

from pathlib import Path

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.providers import (
    ChatProvider,
    EmbeddingProvider,
    MockChatProvider,
    MockEmbeddingProvider,
    OpenAIChatProvider,
    OpenAIEmbeddingProvider,
)
from app.services.queue import ProcessingQueue, get_queue
from app.services.storage import FilingStorage, get_storage


def get_filing_storage(settings: Settings = Depends(get_settings)) -> FilingStorage:
    return get_storage(settings)


def get_processing_queue(settings: Settings = Depends(get_settings)) -> ProcessingQueue:
    return get_queue(settings)


def get_embedding_provider(settings: Settings = Depends(get_settings)) -> EmbeddingProvider:
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings")
        return OpenAIEmbeddingProvider(settings.openai_api_key, settings.embedding_model)
    return MockEmbeddingProvider()


def get_chat_provider(settings: Settings = Depends(get_settings)) -> ChatProvider:
    if settings.chat_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI chat")
        prompt = Path("app/prompts/answer_system.txt").read_text(encoding="utf-8")
        return OpenAIChatProvider(settings.openai_api_key, settings.chat_model, prompt)
    return MockChatProvider()
