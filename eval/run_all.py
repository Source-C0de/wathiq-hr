"""Convenience runner: regenerate golden set, then run retrieval + LLM evals."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> None:
    print(f"\n>>> {' '.join(args)}\n")
    subprocess.check_call([sys.executable, *args], cwd=str(ROOT))


def main() -> int:
    _run(["eval/generate_golden.py"])
    _run(["eval/retrieval_eval.py"])
    _run(["eval/llm_eval.py"])
    print("\nAll evaluation steps finished. See eval/results.*.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())