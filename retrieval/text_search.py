"""BM25 (MinSearch) baseline retriever."""
from __future__ import annotations

from typing import Iterable

from minsearch import Index

from .store import ChunkRecord, fetch_all_chunks, yield_chunks

_INDEX: Index | None = None


def _get_index() -> Index:
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    records: list[ChunkRecord] = fetch_all_chunks()
    idx = Index(text_fields=["text"], keyword_fields=["source_id", "language", "article_no"])
    idx.fit(yield_chunks(records))
    _INDEX = idx
    return idx


def search(query: str, top_k: int = 5, filter_expr: str | None = None) -> list[dict]:
    idx = _get_index()
    boost = {"text": 1.0}
    results = idx.search(
        query=query,
        boost_dict=boost,
        num_results=top_k,
        filter_dict=None,
    )
    return results


if __name__ == "__main__":  # quick CLI smoke test
    import sys

    q = " ".join(sys.argv[1:]) or "annual leave days"
    for hit in search(q):
        print(hit["id"], hit.get("article_no"), hit["text"][:120], "...")