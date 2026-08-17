"""Optional helper: download source files declared in data/sources.csv.

Only writes files that don't exist locally. Use --force to overwrite.

Run from the project root with one of:
    python -m ingest.download_sources
    PYTHONPATH=. python ingest/download_sources.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

# Allow `python ingest/download_sources.py` to find the `ingest` package.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingest.loaders import load_sources_csv  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch raw sources")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--sources", default="data/sources.csv")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    rows = load_sources_csv(args.sources)
    for row in rows:
        url = row.get("url")
        path = row.get("file")
        if not url or not path:
            continue
        if os.path.exists(path) and not args.force:
            print(f"[skip] {path} already exists")
            continue
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        print(f"[get ] {url} -> {path}")
        try:
            with requests.get(url, timeout=args.timeout, stream=True) as r:
                r.raise_for_status()
                with open(path, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            fh.write(chunk)
        except Exception as exc:  # noqa: BLE001
            print(f"[fail] {row['source_id']}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())