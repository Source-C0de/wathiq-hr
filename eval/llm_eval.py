"""LLM-as-judge evaluation: score answer relevance, faithfulness, and citation
accuracy across prompt variants on the golden set.

Writes `eval/results.llm.json` with the leaderboard.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from openai import OpenAI

from app.rag import answer_question
from eval.generate_golden import GOLDEN, write_csv

load_dotenv()
write_csv()

JUDGE_PROMPT = """You are a strict evaluator for a Saudi Labour Law RAG assistant.

Given the question, the reference source/article, and the assistant's answer
(with retrieved contexts), score the answer on three 0-3 rubrics:

- relevance (0-3): does the answer address the user's question?
- faithfulness (0-3): are all claims supported by the retrieved contexts? (0 if fabricated)
- citation (0-3): does the answer cite the correct source/article?

Output ONLY a JSON object: {"relevance": N, "faithfulness": N, "citation": N}

Question: {q}
Reference source: {ref_source}, article: {ref_article}
Assistant answer: {ans}
Contexts:
{ctx}
"""

_CITATION_RX = re.compile(r"\[(\d+)\]")


def _format_context(hits) -> str:
    return "\n\n".join(
        f"[{i+1}] {h.get('source_id')} art={h.get('article_no')}: {h.get('text','')[:300]}"
        for i, h in enumerate(hits)
    )


def _parse_scores(raw: str) -> dict[str, int]:
    try:
        m = re.search(r"\{.*?\}", raw, re.S)
        if not m:
            return {"relevance": 0, "faithfulness": 0, "citation": 0}
        obj = json.loads(m.group(0))
        return {
            "relevance": int(obj.get("relevance", 0)),
            "faithfulness": int(obj.get("faithfulness", 0)),
            "citation": int(obj.get("citation", 0)),
        }
    except Exception:
        return {"relevance": 0, "faithfulness": 0, "citation": 0}


def evaluate_variant(variant: str, judge: OpenAI, judge_model: str) -> dict:
    rel = faith = cite = 0
    per_q: list[dict] = []
    for q in GOLDEN:
        ans = answer_question(q["question"], language=q["language"], prompt_variant=variant)
        ctx = _format_context(
            [{"source_id": c.source_id, "article_no": c.article_no, "text": c.text} for c in ans.citations]
        )
        prompt = JUDGE_PROMPT.format(
            q=q["question"],
            ref_source=q["expected_source_id"],
            ref_article=q.get("expected_article_no"),
            ans=ans.text,
            ctx=ctx or "(no context)",
        )
        resp = judge.chat.completions.create(
            model=judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        scores = _parse_scores(resp.choices[0].message.content)
        rel += scores["relevance"]
        faith += scores["faithfulness"]
        cite += scores["citation"]
        per_q.append({"id": q["id"], **scores})

    n = len(GOLDEN)
    return {
        "variant": variant,
        "avg_relevance": round(rel / n, 3),
        "avg_faithfulness": round(faith / n, 3),
        "avg_citation": round(cite / n, 3),
        "per_question": per_q,
    }


def main() -> int:
    judge = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    judge_model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

    variants = ["strict", "balanced", "balanced"]  # balanced tested twice with different seeds? keep one
    variants = ["strict", "balanced"]

    results = [evaluate_variant(v, judge, judge_model) for v in variants]
    leaderboard = sorted(
        results,
        key=lambda r: (r["avg_faithfulness"], r["avg_relevance"], r["avg_citation"]),
        reverse=True,
    )
    print(f"\n{'variant':12s} {'rel':>6s} {'faith':>6s} {'cite':>6s}")
    print("-" * 36)
    for r in leaderboard:
        print(
            f"{r['variant']:12s} {r['avg_relevance']:>6.2f} "
            f"{r['avg_faithfulness']:>6.2f} {r['avg_citation']:>6.2f}"
        )

    Path("eval").mkdir(exist_ok=True)
    Path("eval/results.llm.json").write_text(
        json.dumps(leaderboard, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nBest variant: {leaderboard[0]['variant']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())