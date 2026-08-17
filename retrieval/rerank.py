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
    """Return a score per document. Higher is better."""
    model = _model()
    # fastembed's TextCrossEncoder.rerank returns an iterator of (doc, score) pairs.
    pairs = list(model.rerank(query, list(documents)))
    # Preserve the input order regardless of how the API returns them.
    score_by_text = {text: float(score) for text, score in pairs}
    scores = [score_by_text.get(d, 0.0) for d in documents]
    if top_k is not None:
        scores = scores[:top_k]
    return scores


if __name__ == "__main__":
    docs = ["Annual leave is 21 days.", "Probation may not exceed 90 days."]
    print(rerank("How long is annual leave?", docs))