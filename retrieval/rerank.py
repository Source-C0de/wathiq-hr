"""Cross-encoder reranker using fastembed (CPU-friendly, no GPU needed)."""
from __future__ import annotations

import os
from typing import Sequence

from fastembed import TextCrossEncoder


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
    scores = list(model.rerank(query, list(documents)))
    # fastembed returns list of float-like scores in the same order as input.
    return [float(s) for s in scores[: top_k or len(documents)]]


if __name__ == "__main__":
    docs = ["Annual leave is 21 days.", "Probation may not exceed 90 days."]
    print(rerank("How long is annual leave?", docs))