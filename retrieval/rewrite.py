"""Optional query rewriting step: normalize Arabic/English phrasing and
expand abbreviations (e.g. EOSB, WPS, GOSI) before retrieval.

Uses gpt-4o-mini; falls back to the raw query on any error so the pipeline
stays robust. The OpenAI client is cached as a module-level singleton so
we don't re-do the TLS handshake / connection-pool warm-up on every call.
"""
from __future__ import annotations

import os

from openai import OpenAI


_PROMPT = """You rewrite user questions about Saudi labour law into a clean,
search-friendly form. Keep the same language as the input.

Rules:
- Expand Saudi-HR abbreviations: EOSB (End of Service Benefits), WPS (Wage
  Protection System), GOSI (General Organization for Social Insurance), HRSD
  (Ministry of Human Resources and Social Development).
- Replace colloquial phrases with the canonical Saudi labour law terms
  (e.g. "end of service" -> "end-of-service benefits / مكافأة نهاية الخدمة").
- Preserve the user's language (Arabic or English).
- Output only the rewritten query, no commentary.

User query: {q}
Rewritten:"""


_CLIENT: OpenAI | None = None


def _client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _CLIENT


def rewrite(query: str, model: str | None = None) -> str:
    if not query.strip():
        return query
    try:
        mdl = model or os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
        resp = _client().chat.completions.create(
            model=mdl,
            messages=[{"role": "user", "content": _PROMPT.format(q=query)}],
            temperature=0.0,
            max_tokens=120,
        )
        return resp.choices[0].message.content.strip() or query
    except Exception:
        return query


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "what's my eosb if i worked 5 yrs"
    print(rewrite(q))