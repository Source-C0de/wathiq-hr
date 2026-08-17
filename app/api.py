"""Optional FastAPI service mirroring the Streamlit chat pipeline.

Run with:
    uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

POST /ask  body: {"query": "...", "language": "en", "top_k": 5}
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import answer_question  # noqa: E402
from monitoring import db as mdb  # noqa: E402

load_dotenv()
mdb.init_db()

app = FastAPI(title="HRAI – Saudi Labour Law API", version="0.1.0")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=2)
    language: str | None = Field(default=None, pattern="^(en|ar)$")
    top_k: int = Field(default=5, ge=1, le=10)
    use_rerank: bool = True
    use_rewriter: bool = True


class CitationOut(BaseModel):
    source_id: str
    article_no: str | None
    url: str
    text: str


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    latency_ms: int
    language: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    try:
        ans = answer_question(
            req.query,
            language=req.language,
            top_k=req.top_k,
            use_rewriter=req.use_rewriter,
            use_rerank=req.use_rerank,
        )
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=f"Missing config: {exc}") from exc

    mdb.log_query(
        lang=req.language or "en",
        query=req.query,
        retrieved_ids=[c.source_id for c in ans.citations],
        latency_ms=ans.latency_ms,
        answered=ans.answered,
    )

    return AskResponse(
        answer=ans.text,
        citations=[
            CitationOut(
                source_id=c.source_id,
                article_no=c.article_no,
                url=c.url,
                text=c.text,
            )
            for c in ans.citations
        ],
        latency_ms=ans.latency_ms,
        language=req.language or "en",
    )