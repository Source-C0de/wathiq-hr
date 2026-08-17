"""CLI entrypoint: `python ingest/run_pipeline.py [--reset]`.

Drops the Qdrant collection when `--reset` is passed, then runs the full
extract -> chunk -> (embed via dlt) -> load pipeline.
"""
from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv
from qdrant_client import QdrantClient


def reset_collection(client: QdrantClient, name: str) -> None:
    try:
        client.delete_collection(collection_name=name)
        print(f"[reset] dropped collection '{name}'")
    except Exception as exc:  # noqa: BLE001
        print(f"[reset] collection '{name}' not present ({exc.__class__.__name__})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Wathiq HR ingest pipeline")
    parser.add_argument("--reset", action="store_true", help="Drop collection first")
    args = parser.parse_args()

    load_dotenv()

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("QDRANT_COLLECTION", "wathiq_hr_law")

    client = QdrantClient(host=host, port=port, timeout=60.0)
    if args.reset:
        reset_collection(client, collection)

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingest.load_law import build_pipeline, chunks_resource  # noqa: E402

    pipeline = build_pipeline()
    # dlt consumes the resource lazily. The qdrant destination produces the
    # embeddings itself (BAAI/bge-small-en, 384-dim) from the `text` field.
    load_info = pipeline.run(chunks_resource())
    print(load_info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
