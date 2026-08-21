from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    api_version: str = "v1"
    database_url: PostgresDsn | str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rag"
    gcp_project_id: str | None = None
    gcs_bucket_name: str = "local-filings"
    cloud_tasks_queue: str | None = None
    cloud_tasks_location: str | None = None
    worker_url: str = "http://worker:8080/api/v1/worker/process"
    worker_oidc_service_account: str | None = None
    max_upload_bytes: int = 25 * 1024 * 1024
    local_auth_enabled: bool = False
    firebase_project_id: str | None = None
    embedding_provider: Literal["mock", "openai"] = "mock"
    chat_provider: Literal["mock", "openai"] = "mock"
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None
    local_storage_dir: str = ".local/gcs"
    request_id_header: str = "x-request-id"
    retrieval_top_k: int = Field(8, ge=1, le=30)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
