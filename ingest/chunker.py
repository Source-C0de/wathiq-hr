"""Chunk documents into ~800-token passages with ~100-token overlap.

We keep article boundaries intact when possible: if a document page/section
already mentions an article number, we anchor the chunk to that article and try
not to cross articles inside a single chunk.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import tiktoken

from .loaders import Document

_ENC = tiktoken.get_encoding("cl100k_base")
_TARGET_TOKENS = 800
_OVERLAP_TOKENS = 100

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_ARTICLE_RX = re.compile(
    r"(?im)^\s*(?:المادة|Article|Art\.?)\s*([0-9٠-٩]{1,4})\b"
)
# Sentences split on ., !, ?, or Arabic full stop (۔) / Arabic question mark (؟).
_SENT_RX = re.compile(r"(?<=[.!?؟۔])\s+")


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    article_no: str | None
    language: str
    text: str
    url: str
    page: int | None
    token_count: int


def _num_tokens(text: str) -> int:
    return len(_ENC.encode(text))


def _split_into_units(text: str) -> list[str]:
    """Split text into article-block units when possible."""
    matches = list(_ARTICLE_RX.finditer(text))
    if len(matches) < 2:
        # Treat the whole text as one unit; let sentence splitter handle it.
        return [text]

    units: list[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            units.append(chunk)
    return units


def _split_by_tokens(unit: str, target: int = _TARGET_TOKENS, overlap: int = _OVERLAP_TOKENS) -> list[str]:
    sentences = _SENT_RX.split(unit.strip())
    sentences = [s for s in sentences if s.strip()]
    if not sentences:
        return [unit]

    pieces: list[str] = []
    buf: list[str] = []
    buf_tokens = 0

    for sent in sentences:
        st = _num_tokens(sent)
        if st > target:
            # Sentence alone too long; hard-split by tokens.
            tokens = _ENC.encode(sent)
            for i in range(0, len(tokens), target - overlap):
                pieces.append(_ENC.decode(tokens[i : i + target]))
            continue
        if buf_tokens + st > target and buf:
            pieces.append(" ".join(buf))
            # Overlap: keep last few sentences that fit into overlap window.
            tail: list[str] = []
            tail_tokens = 0
            for s in reversed(buf):
                ts = _num_tokens(s)
                if tail_tokens + ts > overlap:
                    break
                tail.append(s)
                tail_tokens += ts
            buf = list(reversed(tail))
            buf_tokens = tail_tokens
        buf.append(sent)
        buf_tokens += st

    if buf:
        pieces.append(" ".join(buf))
    return pieces


def chunk_documents(docs: Iterable[Document]) -> Iterable[Chunk]:
    """Yield chunks from a stream of Documents."""
    counter = 0
    for doc in docs:
        units = _split_into_units(doc.text)
        for unit in units:
            article_no = _scan_article_no(unit) or doc.article_no
            for piece in _split_by_tokens(unit):
                counter += 1
                chunk_id = f"{doc.source_id}-{counter:06d}"
                yield Chunk(
                    chunk_id=chunk_id,
                    source_id=doc.source_id,
                    article_no=article_no,
                    language=doc.language,
                    text=piece,
                    url=doc.url,
                    page=doc.page,
                    token_count=_num_tokens(piece),
                )


def _scan_article_no(text: str) -> str | None:
    m = _ARTICLE_RX.search(text)
    if not m:
        return None
    return m.group(1).translate(_ARABIC_DIGITS)