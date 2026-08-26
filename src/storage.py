"""Storage abstraction: local disk as the working copy, optionally synced to a GCS
bucket so index artifacts survive Cloud Run cold starts (Cloud Run's local filesystem
is ephemeral — anything not persisted elsewhere is lost when the instance scales to zero).

If GCS_BUCKET is unset, this is a no-op and everything just lives on local disk —
that's the right mode for local dev / running the free-tier demo without a bucket yet.
"""
from __future__ import annotations

import os
from pathlib import Path

STORE_DIR = Path(os.getenv("STORE_DIR", "data/store"))
GCS_BUCKET = os.getenv("GCS_BUCKET")  # e.g. "nse-rag-analyst-index"
GCS_PREFIX = os.getenv("GCS_PREFIX", "index")

_FILES = ["documents.json", "chunks.jsonl", "bm25.pkl", "dense.faiss"]


def _bucket():
    from google.cloud import storage

    client = storage.Client()
    return client.bucket(GCS_BUCKET)


def download() -> None:
    """Pull the latest index artifacts from GCS into local disk. Call at service startup."""
    if not GCS_BUCKET:
        return
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    bucket = _bucket()
    for name in _FILES:
        blob = bucket.blob(f"{GCS_PREFIX}/{name}")
        if blob.exists():
            blob.download_to_filename(str(STORE_DIR / name))


def upload() -> None:
    """Push local index artifacts to GCS. Call after every ingest/delete that rebuilds the index."""
    if not GCS_BUCKET:
        return
    bucket = _bucket()
    for name in _FILES:
        path = STORE_DIR / name
        if path.exists():
            bucket.blob(f"{GCS_PREFIX}/{name}").upload_from_filename(str(path))
