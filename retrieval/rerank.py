"""Cross-encoder reranker using fastembed (CPU-friendly, no GPU needed).

fastembed 0.5+ exposes the cross-encoder at
``fastembed.rerank.cross_encoder.TextCrossEncoder`` (not at the top level).

Default model is ``Xenova/ms-marco-MiniLM-L-6-v2`` (80 MB) — the same family
used by the original course minsearch module. It's English-focused, ~14× faster
than the multilingual `jinaai/jina-reranker-v2-base-multilingual` (1.1 GB),
and produces a much faster cold start on memory-constrained deployments.

Arabic queries are still served well by the BM25 leg of the hybrid retriever;
the cross-encoder mainly re-orders the fused top candidates.

Set ``WATHIQ_RERANK_MODEL=jinaai/jina-reranker-v2-base-multilingual`` if you
want the heavier multilingual model instead.
"""
from __future__ import annotations

import os
from typing import Sequence

from fastembed.rerank.cross_encoder import TextCrossEncoder


_MODEL: TextCrossEncoder | None = None


def _model() -> TextCrossEncoder:
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    model_name = os.getenv("WATHIQ_RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2")
    _MODEL = TextCrossEncoder(model_name=model_name)
    return _MODEL


def rerank(query: str, documents: Sequence[str], top_k: int | None = None) -> list[float]:
    """Return a score per document. Higher is better.

    In fastembed 0.5.x, ``TextCrossEncoder.rerank`` returns a list of floats
    aligned with the input documents (not a list of (doc, score) tuples).
    """
    model = _model()
    scores = [float(s) for s in model.rerank(query, list(documents))]
    if top_k is not None:
        scores = scores[:top_k]
    return scores


if __name__ == "__main__":
    docs = ["Annual leave is 21 days.", "Probation may not exceed 90 days."]
    print(rerank("How long is annual leave?", docs))