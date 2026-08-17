"""Cross-encoder reranker using fastembed (CPU-friendly, no GPU needed).

fastembed 0.5+ exposes the cross-encoder at
``fastembed.rerank.cross_encoder.TextCrossEncoder`` (not at the top level).
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
    _MODEL = TextCrossEncoder(model_name="jinaai/jina-reranker-v2-base-multilingual")
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