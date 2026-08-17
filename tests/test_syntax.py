"""Static check: every module in the repo imports without error using a
minimal stub set. Useful in CI before installing the full dependency tree.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- Minimal stubs for heavy / optional third-party deps ---------------------
def _stub(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class _Dummy:
    def __init__(self, *_, **__):
        pass

    def __getattr__(self, item):
        return _Dummy()

    def __call__(self, *_, **__):
        return _Dummy()


_stub("openai", OpenAI=_Dummy, embeddings=_Dummy(), chat=_Dummy())
_stub("tiktoken", get_encoding=lambda *_a, **_k: _Dummy())
_stub("pypdf", PdfReader=_Dummy)
_stub("bs4", BeautifulSoup=_Dummy)
_stub("lxml")
_stub("dotenv", load_dotenv=lambda *_a, **_k: None)
_stub("minsearch", Index=_Dummy)

# qdrant_client shim
qdrant_pkg = _stub("qdrant_client")
qdrant_pkg.QdrantClient = _Dummy  # type: ignore[attr-defined]
qdrant_http = _stub("qdrant_client.http")
qdrant_http_models = _stub("qdrant_client.http.models")
qdrant_http_models.Filter = _Dummy  # type: ignore[attr-defined]
qdrant_http_models.FieldCondition = _Dummy  # type: ignore[attr-defined]
qdrant_http_models.MatchValue = _Dummy  # type: ignore[attr-defined]

# dlt + destinations
dlt_mod = _stub("dlt")
dlt_mod.resource = lambda *a, **k: (lambda f: f)
dlt_mod.pipeline = _Dummy
dlt_dest = _stub("dlt.destinations")
dlt_dest.qdrant = _Dummy

# Streamlit (only loaded by UI scripts, not by tests)
_stub("streamlit")
_stub("pandas")
_stub("altair")
_stub("fastapi", FastAPI=_Dummy, HTTPException=_Dummy)
_stub("pydantic", BaseModel=_Dummy, Field=_Dummy)
_stub("uvicorn")
_stub("fastembed", TextCrossEncoder=_Dummy)


sys.path.insert(0, str(ROOT))

MODULES = [
    "ingest.loaders",
    "ingest.chunker",
    "ingest.load_law",
    "ingest.run_pipeline",
    "ingest.download_sources",
    "retrieval.store",
    "retrieval.text_search",
    "retrieval.vector_search",
    "retrieval.rerank",
    "retrieval.hybrid",
    "retrieval.rewrite",
    "monitoring.db",
    "app.rag",
    "app.api",
]


def main() -> int:
    failures = []
    for name in MODULES:
        try:
            importlib.import_module(name)
            print(f"OK   {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name}: {exc.__class__.__name__}: {exc}")
            failures.append(name)
    if failures:
        print(f"\n{len(failures)} module(s) failed: {failures}")
        return 1
    print(f"\nAll {len(MODULES)} modules imported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())