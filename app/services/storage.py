from __future__ import annotations

from pathlib import Path

from app.core.config import Settings


class FilingStorage:
    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError

    async def download_to_path(self, gcs_path: str, destination: str) -> None:
        raise NotImplementedError


class LocalFilingStorage(FilingStorage):
    def __init__(self, root: str):
        self.root = Path(root)

    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return f"local://{path}"

    async def download_to_path(self, gcs_path: str, destination: str) -> None:
        source = self.root / gcs_path.removeprefix("local://")
        Path(destination).write_bytes(source.read_bytes())


class GcsFilingStorage(FilingStorage):
    def __init__(self, bucket_name: str):
        from google.cloud import storage

        self.bucket = storage.Client().bucket(bucket_name)

    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        blob = self.bucket.blob(path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket.name}/{path}"

    async def download_to_path(self, gcs_path: str, destination: str) -> None:
        prefix = f"gs://{self.bucket.name}/"
        blob = self.bucket.blob(gcs_path.removeprefix(prefix))
        blob.download_to_filename(destination)


def get_storage(settings: Settings) -> FilingStorage:
    if settings.app_env == "production":
        return GcsFilingStorage(settings.gcs_bucket_name)
    return LocalFilingStorage(settings.local_storage_dir)
