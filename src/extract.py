"""Extract text from an uploaded NSE/BSE annual report PDF, page by page.

Unlike SEC 10-Ks, Indian annual reports don't follow a consistent "Item N" heading
convention, so v1 uses **page number as the citation unit** instead of section — it's
far more robust to inconsistent report layouts and still gives verifiable, clickable-style
citations. Section-heading detection (Directors' Report, MD&A, Notes to Accounts, ...)
can be layered on top later without changing anything downstream.

Output: list of {"page": int, "text": str} — one entry per page with extractable text.
"""
from __future__ import annotations

from pathlib import Path


def extract_pages(pdf_path: str, min_chars: int = 30) -> list[dict]:
    """Return page-level text blocks. Skips near-empty pages (pure images, blank dividers)."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        text = " ".join(text.split())  # collapse whitespace/newlines
        if len(text) >= min_chars:
            pages.append({"page": i, "text": text})
    doc.close()
    if not pages:
        raise RuntimeError(
            "no extractable text found — this PDF may be scanned/image-only and needs OCR "
            "(not implemented in v1)"
        )
    return pages


def write_sample(out_path: str) -> Path:
    """Tiny synthetic filing so the pipeline runs offline with no PDF needed, for local testing."""
    pages = [
        {"page": 1, "text": (
            "Board's Report. Your Directors are pleased to present the Annual Report for "
            "the financial year. The company faces risks from intense competition, raw "
            "material price volatility, and currency fluctuations affecting export revenue. "
            "Cybersecurity incidents could expose customer data and trigger regulatory "
            "action under applicable data protection law.")},
        {"page": 2, "text": (
            "Management Discussion and Analysis. Total revenue from operations increased "
            "16% year over year to Rs. 3,200 crore, driven by growth in the exports segment, "
            "which grew 22%. EBITDA margin expanded 140 basis points to 21.4% on operating "
            "leverage. Finance costs declined due to lower working capital borrowing.")},
        {"page": 3, "text": (
            "The company operates three business segments: textiles, chemicals, and "
            "packaging, with manufacturing facilities in Gujarat, Tamil Nadu, and "
            "Maharashtra. Products are sold domestically and exported to over 40 countries.")},
    ]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    out.write_text("\n".join(json.dumps(p) for p in pages))
    return out
