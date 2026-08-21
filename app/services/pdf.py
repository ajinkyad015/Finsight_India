from __future__ import annotations

from pathlib import Path


def validate_pdf_upload(filename: str | None, content_type: str | None, size: int, max_size: int) -> None:
    if not filename or not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF uploads are supported")
    if content_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"}:
        raise ValueError("Uploaded file must be a PDF")
    if size <= 0:
        raise ValueError("Uploaded file is empty")
    if size > max_size:
        raise ValueError(f"Uploaded file exceeds {max_size} bytes")


def extract_readable_pages(path: str) -> list[tuple[int, str]]:
    import fitz

    pages: list[tuple[int, str]] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append((i, text))
    if not pages:
        raise ValueError("No digitally readable text was found; OCR is out of scope for this prototype")
    return pages


def ensure_pdf_magic(path: str) -> None:
    if Path(path).read_bytes()[:5] != b"%PDF-":
        raise ValueError("Uploaded file does not look like a PDF")
