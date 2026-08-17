"""Dense retrieval against the Qdrant collection."""
from __future__ import annotations

import os
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


def _client() -> QdrantClient:
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port, timeout=60.0)


def _embed(query: str) -> list[float]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    resp = client.embeddings.create(model=model, input=[query])
    return resp.data[0].embedding


def search(query: str, top_k: int = 5, language: str | None = None) -> list[dict[str, Any]]:
    qclient = _client()
    collection = os.getenv("QDRANT_COLLECTION", "hrai_saudi_labour_law")

    # If the KB has never been ingested, return empty so the chat still works.
    try:
        qclient.get_collection(collection_name=collection)
    except Exception:
        return []

    vector = _embed(query)

    flt = None
    if language:
        flt = qm.Filter(must=[qm.FieldCondition(key="language", match=qm.MatchValue(value=language))])

    hits = qclient.search(
        collection_name=collection,
        query_vector=vector,
        limit=top_k,
        query_filter=flt,
        with_payload=True,
    )
    out: list[dict[str, Any]] = []
    for h in hits:
        p = h.payload or {}
        out.append(
            {
                "id": str(h.id),
                "score": float(h.score),
                "source_id": p.get("source_id"),
                "article_no": p.get("article_no"),
                "language": p.get("language", "en"),
                "text": p.get("text", ""),
                "url": p.get("url", ""),
                "page": p.get("page"),
            }
        )
    return out


if __name__ == "__main__":  # CLI smoke test
    import sys

    q = " ".join(sys.argv[1:]) or "notice period during probation"
    for hit in search(q):
        print(f"{hit['score']:.3f} {hit['id']} art={hit['article_no']} {hit['text'][:120]}...")