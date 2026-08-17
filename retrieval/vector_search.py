"""Dense retrieval against the Qdrant collection.

Embeddings are produced by the same model used by the dlt qdrant destination
at ingest time: ``BAAI/bge-small-en`` (384-dim, fastembed). Keeping the
embedding model identical to the one used at ingest ensures the vector
dimensions match and the cosine similarity is meaningful.
"""
from __future__ import annotations

import os
from typing import Any

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


_VECTOR_NAME = "fast-bge-small-en"
_EMBED_MODEL = "BAAI/bge-small-en"


def _client() -> QdrantClient:
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port, timeout=60.0)


_ENCODER: TextEmbedding | None = None


def _model() -> TextEmbedding:
    global _ENCODER
    if _ENCODER is not None:
        return _ENCODER
    _ENCODER = TextEmbedding(model_name=_EMBED_MODEL)
    return _ENCODER


def _embed(query: str) -> list[float]:
    model = _model()
    # fastembed returns a generator; take the first (and only) embedding.
    vec = next(iter(model.embed([query])))
    return vec.tolist()


def search(query: str, top_k: int = 5, language: str | None = None) -> list[dict[str, Any]]:
    qclient = _client()
    # dlt's qdrant destination creates the actual collection as
    # `{dataset}_{resource_name}` — for our `chunks` resource that's
    # `wathiq_hr_law_chunks`.
    base = os.getenv("QDRANT_COLLECTION", "wathiq_hr_law")
    collection = f"{base}_chunks"

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
        query_vector=(_VECTOR_NAME, vector),
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
