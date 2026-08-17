"""File loaders: read PDFs and HTML files from data/raw/ into structured records.

Each loader returns a dict with at least:
  source_id (str), article_no (str|None), title (str|None),
  language (str), text (str), url (str), page (int|None)
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from bs4 import BeautifulSoup


@dataclass
class Document:
    source_id: str
    text: str
    language: str
    url: str
    article_no: str | None = None
    title: str | None = None
    page: int | None = None


_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_ARTICLE_RX = re.compile(
    r"(?im)^\s*(?:المادة|Article|Art\.?)\s*([0-9٠-٩]{1,4})\b"
)


def load_sources_csv(path: str | Path = "data/sources.csv") -> list[dict]:
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def _detect_language(text: str) -> str:
    # Cheap heuristic: ratio of Arabic Unicode code points.
    if not text:
        return "en"
    arabic = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
    return "ar" if arabic / max(len(text), 1) > 0.15 else "en"


def _scan_article_no(text: str) -> str | None:
    m = _ARTICLE_RX.search(text)
    if not m:
        return None
    return m.group(1).translate(_ARABIC_DIGITS)


def load_pdf(path: str | Path, source_id: str, url: str) -> Iterator[Document]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    for page_idx, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        yield Document(
            source_id=source_id,
            text=text,
            language=_detect_language(text),
            url=url,
            article_no=_scan_article_no(text),
            title=None,
            page=page_idx,
        )


def load_html(path: str | Path, source_id: str, url: str) -> Iterator[Document]:
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "lxml")
    # Drop noisy tags
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else None

    # Prefer an article-ish container; fall back to body text.
    container = soup.find("article") or soup.find("main") or soup.body or soup
    for block in container.find_all(
        ["h1", "h2", "h3", "section", "div", "p", "li"], recursive=True
    ):
        block_text = block.get_text(" ", strip=True)
        if len(block_text) < 40:  # skip nav noise
            continue
        yield Document(
            source_id=source_id,
            text=block_text,
            language=_detect_language(block_text),
            url=url,
            article_no=_scan_article_no(block_text),
            title=title,
            page=None,
        )


def load_markdown(path: str | Path, source_id: str, url: str) -> Iterator[Document]:
    """Yield one Document per markdown section (split on H1/H2 headings).

    Front-matter (YAML between leading `---` fences) is stripped. Fenced code
    blocks are preserved in-line so the chunker can still see them.
    """
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")

    # Strip YAML front-matter
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            raw = raw[end + 4 :]

    # Title = first H1 if present
    title: str | None = None
    lines = raw.splitlines()
    for line in lines:
        if line.lstrip().startswith("# "):
            title = line.lstrip("# ").strip()
            break

    # Split on H1/H2 boundaries so each chunk carries section context.
    current_title = title
    current_lines: list[str] = []
    current_article: str | None = None

    def _flush() -> Iterator[Document]:
        nonlocal current_title, current_lines, current_article
        body = "\n".join(current_lines).strip()
        current_lines = []
        if not body:
            return iter(())
        # Prepend the section title so the chunk stays self-contained.
        text = f"{current_title}\n{body}" if current_title else body
        yield Document(
            source_id=source_id,
            text=text,
            language=_detect_language(text),
            url=url,
            article_no=current_article or _scan_article_no(body),
            title=current_title,
            page=None,
        )
        current_article = None

    for line in lines:
        if line.lstrip().startswith(("# ", "## ")):
            yield from _flush()
            heading = line.lstrip("# ").strip()
            current_title = heading
            current_article = _scan_article_no(heading)
        else:
            current_lines.append(line)
    yield from _flush()


def load_file(path: str | Path, source_id: str, url: str) -> Iterator[Document]:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        yield from load_pdf(p, source_id, url)
    elif suffix in {".html", ".htm"}:
        yield from load_html(p, source_id, url)
    elif suffix in {".md", ".markdown"}:
        yield from load_markdown(p, source_id, url)
    elif suffix in {".txt"}:
        yield from load_markdown(p, source_id, url)  # plain text reuses section splitter
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")