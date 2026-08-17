"""dlt pipeline: extract -> chunk -> embed -> load into Qdrant.

We use dlt for orchestration (resource + destination) so the ingestion step is
auditable, resumable, and matches the LLM Zoomcamp rubric for automated
ingestion.
"""
from __future__ import annotations

import os
from typing import Iterator

import dlt
from dlt.destinations import qdrant
from openai import OpenAI

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
    """Yield one record per chunk, embedding each via OpenAI."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    embed_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "32"))

    sources = load_sources_csv(sources_csv)
    pending: list[Chunk] = []
    yielded = 0

    # Count sources that actually have a file on disk — if none, abort early
    # so dlt's `write_disposition="replace"` doesn't wipe the existing KB.
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
            for chunk in chunk_documents([doc]):
                pending.append(chunk)

                if len(pending) >= batch_size:
                    yield from _flush(pending, client, embed_model, yielded)
                    yielded += len(pending)
                    pending = []

    if pending:
        yield from _flush(pending, client, embed_model, yielded)


def _flush(
    pending: list[Chunk],
    client: OpenAI,
    model: str,
    started: int,
) -> Iterator[dict]:
    """Embed a batch and yield one record per chunk. Pure generator."""
    texts = [c.text for c in pending]
    resp = client.embeddings.create(model=model, input=texts)
    vectors = [d.embedding for d in resp.data]

    for chunk, vector in zip(pending, vectors):
        yield {
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "article_no": chunk.article_no,
            "language": chunk.language,
            "text": chunk.text,
            "url": chunk.url,
            "page": chunk.page,
            "token_count": chunk.token_count,
            "vector": vector,
        }


def build_pipeline():
    """Construct (but do not run) the dlt pipeline."""
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("QDRANT_COLLECTION", "hrai_saudi_labour_law")

    # dlt's qdrant destination expects a credentials dict with `location`.
    # Passing a bare string here leaves `location=None`, so the underlying
    # QdrantClient falls back to localhost (Connection refused inside Docker).
    location = f"http://{qdrant_host}:{qdrant_port}"
    destination = qdrant(credentials={"location": location})
    return dlt.pipeline(
        pipeline_name="hrai_law_ingest",
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