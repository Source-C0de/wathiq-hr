"""Retrieval evaluation: hit-rate and MRR over the golden Q&A set.

Compares BM25, dense (Qdrant), and hybrid (RRF + cross-encoder rerank) and
prints a small leaderboard. Writes `eval/results.retrieval.json`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from eval.generate_golden import GOLDEN, write_csv
from retrieval import hybrid, text_search, vector_search

load_dotenv()
GOLDEN_PATH = write_csv()


def _hit_and_rr(retrieved: list[dict], expected_source: str, expected_article: str | None) -> tuple[int, float]:
    for rank, hit in enumerate(retrieved, start=1):
        if hit.get("source_id") != expected_source:
            continue
        if expected_article is None:
            return 1, 1.0 / rank
        if str(hit.get("article_no")) == str(expected_article):
            return 1, 1.0 / rank
    return 0, 0.0


def evaluate(name: str, search_fn: Callable, **kwargs) -> dict:
    hits = 0
    rr_sum = 0.0
    per_q: list[dict] = []
    for q in GOLDEN:
        retrieved = search_fn(q["question"], **kwargs)
        h, rr = _hit_and_rr(retrieved, q["expected_source_id"], q.get("expected_article_no"))
        hits += h
        rr_sum += rr
        per_q.append(
            {
                "id": q["id"],
                "question": q["question"],
                "hit": h,
                "rr": rr,
                "top1": retrieved[0].get("source_id") if retrieved else None,
            }
        )

    n = len(GOLDEN)
    return {
        "name": name,
        "hit_rate": round(hits / n, 4),
        "mrr": round(rr_sum / n, 4),
        "per_question": per_q,
    }


def main() -> int:
    candidate_k = 5

    results = []
    results.append(evaluate("bm25", text_search.search, top_k=candidate_k))
    results.append(
        evaluate("dense_qdrant", vector_search.search, top_k=candidate_k)
    )
    results.append(
        evaluate(
            "hybrid_rrf_rerank",
            lambda q, top_k: hybrid.hybrid_search(q, top_k=top_k, use_rerank=True),
            top_k=candidate_k,
        )
    )

    leaderboard = sorted(results, key=lambda r: (r["hit_rate"], r["mrr"]), reverse=True)
    print(f"\n{'retriever':30s} {'hit_rate':>10s} {'mrr':>8s}")
    print("-" * 50)
    for r in leaderboard:
        print(f"{r['name']:30s} {r['hit_rate']:>10.4f} {r['mrr']:>8.4f}")

    Path("eval").mkdir(exist_ok=True)
    Path("eval/results.retrieval.json").write_text(
        json.dumps(leaderboard, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nBest retriever: {leaderboard[0]['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())