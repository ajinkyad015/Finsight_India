"""FastAPI service: upload NSE annual reports, list/delete them, ask grounded+cited questions.

CORS is open here for demo simplicity — lock ALLOWED_ORIGINS down to your actual frontend
origin before this is anything more than a portfolio project.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.pipeline import RAGPipeline

app = FastAPI(title="NSE Annual Report RAG Analyst", version="0.1.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

_pipe = RAGPipeline()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    doc_ids: list[str] | None = None  # None / omitted -> search across all uploaded reports
    top_k: int = Field(5, ge=1, le=20)
    rerank: bool = True


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    company: str = Form(...),
    year: str = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "only PDF uploads are supported in v1")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        meta = _pipe.ingest(tmp_path, company, year, file.filename)
    except RuntimeError as e:
        raise HTTPException(422, str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return meta


@app.get("/documents")
def get_documents():
    return _pipe.documents()


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    _pipe.delete(doc_id)
    return {"deleted": doc_id}


@app.post("/ask")
def ask(req: AskRequest):
    return _pipe.ask(req.question, req.doc_ids, top_k=req.top_k, rerank=req.rerank)
