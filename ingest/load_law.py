"""dlt pipeline: extract -> chunk -> load into Qdrant.

Embeddings are produced by dlt's qdrant destination itself (fastembed's
`BAAI/bge-small-en`, 384-dim). The resource just yields plain records with a
`text` field tagged with `VECTORIZE_HINT` so dlt knows what to embed.
"""
from __future__ import annotations

import os
from typing import Iterator

import dlt
from dlt.destinations import qdrant
from dlt.destinations.impl.qdrant.qdrant_adapter import qdrant_adapter, VECTORIZE_HINT

from .chunker import Chunk, chunk_documents
from .loaders import Document, load_file, load_sources_csv


@dlt.resource(
    name="chunks",
    write_disposition="replace",
    primary_key="chunk_id",
)
def chunks_resource(
    sources_csv: str = "data/sources.csv",
    data_root: str = "data/raw",
) -> Iterator[dict]:
    """Yield one record per chunk. dlt will embed the `text` field for us."""
    sources = load_sources_csv(sources_csv)

    # If no source files are present, abort early so dlt's
    # `write_disposition="replace"` doesn't wipe the existing KB.
    available = [s for s in sources if s.get("file") and os.path.exists(s["file"])]
    if not available:
        print(
            f"[ingest] no source files found in {data_root} for {len(sources)} "
            "entries in sources.csv — skipping ingestion to preserve existing KB."
        )
        return

    for src in sources:
        path = src["file"]
        if not path or not os.path.exists(path):
            print(f"[ingest] missing file for {src['source_id']}: {path} -- skipping")
            continue

        for doc in load_file(path, src["source_id"], src["url"]):
            yield from chunk_documents([doc])


# Adapter marks the `text` field for dlt's qdrant destination to embed.
chunks_resource = qdrant_adapter(
    chunks_resource,
    embed=["text"],
)


def build_pipeline():
    """Construct (but do not run) the dlt pipeline."""
    collection = os.getenv("QDRANT_COLLECTION", "wathiq_hr_law")
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    location = f"http://{qdrant_host}:{qdrant_port}"

    # `qdrant` destination expects `credentials={"location": ...}` in dlt 0.5.x.
    destination = qdrant(credentials={"location": location})
    return dlt.pipeline(
        pipeline_name="wathiq_law_ingest",
        destination=destination,
        dataset_name=collection,
        progress="log",
    )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    pipeline = build_pipeline()
    load_info = pipeline.run(chunks_resource())
    print(load_info)


def build_pipeline():
    """Construct (but do not run) the dlt pipeline."""
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("QDRANT_COLLECTION", "wathiq_hr_law")

    # dlt's qdrant destination expects a credentials dict with `location`.
    # Passing a bare string here leaves `location=None`, so the underlying
    # QdrantClient falls back to localhost (Connection refused inside Docker).
    location = f"http://{qdrant_host}:{qdrant_port}"
    destination = qdrant(credentials={"location": location})
    return dlt.pipeline(
        pipeline_name="wathiq_law_ingest",
        destination=destination,
        dataset_name=collection,
        progress="log",
    )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    pipeline = build_pipeline()
    load_info = pipeline.run(chunks_resource())
    print(load_info)