"""Optional helper: download source files declared in data/sources.csv.

Only writes files that don't exist locally. Use --force to overwrite.
"""
from __future__ import annotations

import argparse
import os
import sys

import requests

from ingest.loaders import load_sources_csv


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