"""Hybrid retriever: BM25 + dense, fused with Reciprocal Rank Fusion (RRF),
optionally re-ranked by a cross-encoder."""
from __future__ import annotations

from typing import Any

from .rerank import rerank
from .text_search import search as bm25_search
from .vector_search import search as dense_search


def _rrf(rank_lists: list[list[dict[str, Any]]], k: int = 60) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion across rank lists.

    Each list contributes 1/(k + rank) per hit. We key hits on chunk id.
    """
    scores: dict[str, float] = {}
    meta: dict[str, dict[str, Any]] = {}
    for rank_list in rank_lists:
        for rank, hit in enumerate(rank_list, start=1):
            cid = str(hit["id"])
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            meta.setdefault(cid, hit)
    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    return [{**meta[cid], "rrf_score": scores[cid]} for cid in ranked_ids]


def hybrid_search(
    query: str,
    top_k: int = 5,
    use_rerank: bool = True,
    language: str | None = None,
    candidate_k: int = 20,
) -> list[dict[str, Any]]:
    """Run BM25 + dense, fuse, optionally rerank."""
    bm = bm25_search(query, top_k=candidate_k)
    dn = dense_search(query, top_k=candidate_k, language=language)
    fused = _rrf([bm, dn])

    if not use_rerank:
        return fused[:top_k]

    # Rerank top candidates only — cross-encoder is more expensive.
    cand = fused[: max(top_k * 2, candidate_k)]
    texts = [c["text"] for c in cand]
    scores = rerank(query, texts)
    for c, s in zip(cand, scores):
        c["rerank_score"] = float(s)
    cand.sort(key=lambda x: x["rerank_score"], reverse=True)
    return cand[:top_k]


if __name__ == "__main__":  # CLI smoke test
    import sys

    q = " ".join(sys.argv[1:]) or "how many days of leave per year"
    for hit in hybrid_search(q, top_k=5, use_rerank=True):
        print(hit["id"], hit.get("article_no"), hit["text"][:120], "...")