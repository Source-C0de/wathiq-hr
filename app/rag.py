"""RAG answer generator: retrieval -> prompt -> LLM -> answer + citations.

Two prompt variants are exposed so the LLM evaluation step can compare them:
  - `strict`: refuses to answer if context is insufficient, hard-cites articles.
  - `balanced`: friendlier tone, still requires citations.

Two entry points:
  - `answer_question(query, ...)` — blocking, returns the full `Answer`.
  - `answer_question_stream(query, ...)` — yields text chunks as they arrive
    from the LLM, then a final `(Answer, latency_ms, first_token_ms)` tuple.

The OpenAI client is cached at module scope so we skip the TLS handshake /
connection-pool warm-up on every call.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterator

from openai import OpenAI

from retrieval.hybrid import hybrid_search
from retrieval.rewrite import rewrite


@dataclass
class Citation:
    source_id: str
    article_no: str | None
    url: str
    text: str

    def render(self) -> str:
        art = f", Article {self.article_no}" if self.article_no else ""
        return f"[{self.source_id}{art}]({self.url})"


@dataclass
class Answer:
    text: str
    citations: list[Citation]
    retrieved_ids: list[str]
    latency_ms: int
    answered: bool
    language: str


_PROMPTS: dict[str, str] = {
    "strict": (
        "You are Wathiq HR, a precise assistant for Saudi Labour Law, HR policy, "
        "and employee rights. Answer ONLY using the provided context. If the "
        "context does not contain the answer, reply exactly: "
        "\"I could not find this in the provided sources.\" "
        "Cite the supporting article/source after each factual claim using the "
        "marker [n], where n matches the citation block at the end. "
        "Answer in the same language as the user's question."
    ),
    "balanced": (
        "You are Wathiq HR, a helpful assistant for Saudi Labour Law, HR policy, "
        "and employee rights. Use the provided context to answer the user's "
        "question. If the context is missing the answer, say so honestly rather "
        "than guessing. Cite supporting articles/sources using markers like "
        "[n] that map to the citation list at the end. Match the user's "
        "language. This is general information, not legal advice."
    ),
}


_CLIENT: OpenAI | None = None


def _client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _CLIENT


def _format_context(hits: list[dict]) -> tuple[str, list[Citation]]:
    blocks: list[str] = []
    cites: list[Citation] = []
    for i, hit in enumerate(hits, start=1):
        cites.append(
            Citation(
                source_id=str(hit.get("source_id", "")),
                article_no=hit.get("article_no") or None,
                url=str(hit.get("url", "")),
                text=str(hit.get("text", ""))[:600],
            )
        )
        article = f" (Article {hit['article_no']})" if hit.get("article_no") else ""
        blocks.append(
            f"[{i}] source={hit.get('source_id')} lang={hit.get('language')}{article}\n"
            f"{hit.get('text', '').strip()}"
        )
    return "\n\n".join(blocks), cites


def _build_messages(query: str, context: str, prompt_variant: str) -> list[dict]:
    system = _PROMPTS.get(prompt_variant, _PROMPTS["balanced"])
    user_msg = (
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Remember to cite each factual claim with [n] markers."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg},
    ]


def _retrieve(query: str, top_k: int, use_rewriter: bool, use_rerank: bool, language: str | None) -> list[dict]:
    rewritten = rewrite(query) if use_rewriter else query
    return hybrid_search(rewritten, top_k=top_k, use_rerank=use_rerank, language=language)


def answer_question(
    query: str,
    *,
    language: str | None = None,
    top_k: int = 5,
    use_rewriter: bool = False,  # off by default — saves 500–1500 ms
    use_rerank: bool = True,
    prompt_variant: str = "balanced",
    model: str | None = None,
) -> Answer:
    """End-to-end answer pipeline (non-streaming)."""
    start_t = time.perf_counter()

    hits = _retrieve(query, top_k, use_rewriter, use_rerank, language)
    if not hits:
        return Answer(
            text="I could not find this in the provided sources.",
            citations=[],
            retrieved_ids=[],
            latency_ms=int((time.perf_counter() - start_t) * 1000),
            answered=False,
            language=language or "en",
        )

    context, citations = _format_context(hits)
    messages = _build_messages(query, context, prompt_variant)
    mdl = model or os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

    resp = _client().chat.completions.create(
        model=mdl,
        messages=messages,
        temperature=0.2,
    )
    text = resp.choices[0].message.content.strip()

    return Answer(
        text=text,
        citations=citations,
        retrieved_ids=[c.source_id for c in citations],
        latency_ms=int((time.perf_counter() - start_t) * 1000),
        answered=True,
        language=language or "en",
    )


def answer_question_stream(
    query: str,
    *,
    language: str | None = None,
    top_k: int = 5,
    use_rewriter: bool = False,
    use_rerank: bool = True,
    prompt_variant: str = "balanced",
    model: str | None = None,
) -> Iterator[str | tuple[Answer, int, int]]:
    """Streaming variant of `answer_question`.

    Yields:
      - text chunks (str) as the LLM streams them.
      - A final tuple ``(Answer, latency_ms, first_token_ms)`` once the
        stream completes, carrying the full Answer plus timing info.
    """
    start_t = time.perf_counter()
    first_token_at: int | None = None

    hits = _retrieve(query, top_k, use_rewriter, use_rerank, language)
    if not hits:
        empty = Answer(
            text="I could not find this in the provided sources.",
            citations=[],
            retrieved_ids=[],
            latency_ms=int((time.perf_counter() - start_t) * 1000),
            answered=False,
            language=language or "en",
        )
        yield empty.text
        yield empty, int((time.perf_counter() - start_t) * 1000), 0
        return

    context, citations = _format_context(hits)
    messages = _build_messages(query, context, prompt_variant)
    mdl = model or os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

    stream = _client().chat.completions.create(
        model=mdl,
        messages=messages,
        temperature=0.2,
        stream=True,
    )
    text_parts: list[str] = []
    for chunk in stream:
        # Each chunk has delta.content; concat as they arrive.
        delta = chunk.choices[0].delta if chunk.choices else None
        if not delta or not delta.content:
            continue
        if first_token_at is None:
            first_token_at = int((time.perf_counter() - start_t) * 1000)
        text_parts.append(delta.content)
        yield delta.content

    full_text = "".join(text_parts).strip()
    latency_ms = int((time.perf_counter() - start_t) * 1000)
    answer = Answer(
        text=full_text,
        citations=citations,
        retrieved_ids=[c.source_id for c in citations],
        latency_ms=latency_ms,
        answered=True,
        language=language or "en",
    )
    yield answer, latency_ms, first_token_at or latency_ms


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "How many days of annual leave am I entitled to?"
    ans = answer_question(q)
    print(ans.text)
    print("\nCitations:")
    for c in ans.citations:
        print(" -", c.render())
