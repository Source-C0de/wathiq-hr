"""Shared in-memory chunk store for the lexical (BM25) index.

The Qdrant store stays the source of truth for vectors; this local index mirrors
the same chunks so BM25 + dense share identical text. It is built once from the
Qdrant collection and cached to `data/processed/chunks.jsonl`.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


@dataclass
class ChunkRecord:
    chunk_id: str
    source_id: str
    article_no: str | None
    language: str
    text: str
    url: str
    page: int | None

    def to_dict(self) -> dict:
        return asdict(self)


def _qdrant() -> tuple[QdrantClient, str]:
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("QDRANT_COLLECTION", "hrai_saudi_labour_law")
    return QdrantClient(host=host, port=port, timeout=60.0), collection


def fetch_all_chunks(cache_path: str = "data/processed/chunks.jsonl") -> list[ChunkRecord]:
    """Scroll through the Qdrant collection, returning ChunkRecord list."""
    cache = Path(cache_path)
    if cache.exists() and not os.getenv("HRAI_REBUILD_CACHE"):
        return [ChunkRecord(**json.loads(line)) for line in cache.read_text(encoding="utf-8").splitlines() if line.strip()]

    client, collection = _qdrant()
    cache.parent.mkdir(parents=True, exist_ok=True)

    records: list[ChunkRecord] = []
    next_offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=collection,
            with_vectors=False,
            with_payload=True,
            limit=256,
            offset=next_offset,
        )
        for pt in points:
            payload = pt.payload or {}
            records.append(
                ChunkRecord(
                    chunk_id=str(pt.id),
                    source_id=payload.get("source_id", ""),
                    article_no=payload.get("article_no"),
                    language=payload.get("language", "en"),
                    text=payload.get("text", ""),
                    url=payload.get("url", ""),
                    page=payload.get("page"),
                )
            )
        if next_offset is None:
            break

    cache.write_text(
        "\n".join(json.dumps(r.to_dict(), ensure_ascii=False) for r in records),
        encoding="utf-8",
    )
    return records


def yield_chunks(records: Iterable[ChunkRecord]) -> Iterable[dict]:
    for r in records:
        d = r.to_dict()
        d["id"] = r.chunk_id
        yield d