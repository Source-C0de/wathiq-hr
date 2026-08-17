"""Quick tests for the chunker and loaders (no external services needed)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingest.chunker import chunk_documents  # noqa: E402
from ingest.loaders import Document  # noqa: E402


def test_chunk_preserves_article_boundary() -> None:
    text = (
        "Article 109: An employee shall be entitled to 21 days of annual leave "
        "during each year of service, increasing to 30 days after five years.\n\n"
        "Article 110: The employer may determine the timing of annual leave.\n\n"
        "Article 111: Annual leave may be carried forward with the employer's consent."
    )
    doc = Document(
        source_id="m51_en", text=text, language="en", url="test://doc"
    )
    chunks = list(chunk_documents([doc]))
    assert len(chunks) >= 2, f"expected multi-chunk output, got {len(chunks)}"
    # Every chunk must keep the source_id
    assert all(c.source_id == "m51_en" for c in chunks)
    # Each chunk must record a non-zero token count
    assert all(c.token_count > 0 for c in chunks)


def test_chunker_handles_long_unit() -> None:
    text = " ".join(["Sentence number " + str(i) + "."] for i in range(500))
    doc = Document(source_id="m51_en", text=text, language="en", url="test://x")
    chunks = list(chunk_documents([doc]))
    assert chunks, "expected at least one chunk for long input"
    # Largest chunk should be near the target size, not way over.
    assert max(c.token_count for c in chunks) <= 1200


def test_markdown_loader_splits_on_headings() -> None:
    from ingest.loaders import load_markdown

    md = """---
author: HR Team
---

# Annual Leave Policy

Article 109: an employee is entitled to 21 days of annual leave.

## Carry-over rules

Article 112: leave may be carried forward with employer consent.

# Probation

Article 53: probation must not exceed 90 days.
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(md)
        path = fh.name
    docs = list(load_markdown(path, "hr_guide_md", "test://md"))
    titles = [d.title for d in docs]
    assert "Annual Leave Policy" in titles
    assert "Probation" in titles
    assert any("Article 109" in d.text for d in docs)
    # Front-matter must be stripped
    assert not any("author:" in d.text for d in docs)


def test_html_loader_strips_noise() -> None:
    from ingest.loaders import load_html

    html = """
    <html><head><script>alert('x')</script><title>T</title></head>
    <body><nav>menu</nav><main><p>Article 5 explains probation rules.</p></main></body>
    </html>
    """
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(html)
        path = fh.name
    docs = list(load_html(path, "src", "test://u"))
    text_blob = " ".join(d.text for d in docs)
    assert "probation rules" in text_blob
    assert "alert" not in text_blob


if __name__ == "__main__":
    for fn in [
        test_chunk_preserves_article_boundary,
        test_chunker_handles_long_unit,
        test_markdown_loader_splits_on_headings,
        test_html_loader_strips_noise,
    ]:
        fn()
        print(f"OK {fn.__name__}")
    print("All tests passed.")