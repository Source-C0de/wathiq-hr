# HRAI – Saudi Labour Law Assistant

> An AI copilot for Saudi Labour Law, HR policy, and employee rights.

HRAI is an end-to-end Retrieval-Augmented Generation (RAG) application that
answers plain-language questions about the Saudi Labour Law (Royal Decree M/51),
HR regulations, and employee rights. It grounds every answer in official
sources and cites the supporting article when available.

It was built as the capstone project for the **DataTalks.Club LLM Zoomcamp**,
aligned to the course evaluation rubric (problem definition, hybrid retrieval,
LLM evaluation, UI, automated ingestion, monitoring, containerization,
reproducibility, best practices).

---

## Problem

Saudi employees, HR teams, and legal advisors routinely need answers to
questions like *"How is end-of-service benefit calculated after 5 years?"* or
*"How many days of annual leave am I entitled to?"*. The authoritative answer
lives in the official Saudi Labour Law and the MHRSD Executive Regulations,
often in Arabic, scattered across PDFs and government portals.

A general-purpose LLM can hallucinate article numbers. HRAI solves this with a
RAG pipeline that retrieves the relevant articles from the law and forces the
LLM to ground its answer in those passages, refusing to guess when the
context is missing.

## Features

- **Bilingual** chat (English / Arabic)
- **Hybrid retrieval** (BM25 + dense + reciprocal-rank fusion + cross-encoder rerank)
- **Query rewriting** that expands Saudi-HR abbreviations (EOSB, WPS, GOSI, …)
- **Citation-backed answers** with link to the source
- **Streamlit UI** with feedback widgets
- **SQLite-backed monitoring dashboard** (6 charts: volume, latency, language split, feedback ratio, top sources, unanswered rate)
- **FastAPI** endpoint at `/ask` for programmatic access
- **One-shot ingestion** via `dlt` straight into Qdrant

## Dataset

Sources are public Saudi government / ILO documents. See `data/sources.csv`
for the full list with URLs, language, and license.

| Source ID | Title | Lang |
|-----------|----------------------------|------|
| `m51_en` | Saudi Labour Law (M/51) – English | en |
| `m51_ar` | نظام العمل – Arabic | ar |
| `exec_reg_ar` | Executive Regulations | ar |
| `gosi_faq_en` | GOSI FAQ | en |
| `wps_en` | Wage Protection System | en |
| `nitaqat_en` | Nitaqat bands | en |
| `female_workers_en` | Women in the workplace | en |
| `remote_work_ar` | Remote work guide | ar |

## Architecture

```
raw PDFs/HTML ──▶ dlt pipeline ──▶ Qdrant (vectors)
                           └────▶ data/processed/chunks.jsonl (BM25)

user ──▶ Streamlit ──▶ Query rewriter ──▶ Hybrid retriever (RRF + rerank)
                                          │
                                          ▼
                                  LLM (gpt-4o-mini) ──▶ answer + citations
                                          │
                                          ▼
                              SQLite logs ──▶ Dashboard
```

See [`docs/architecture.md`](docs/architecture.md) for the full diagram.

## Evaluation (LLM Zoomcamp rubric)

| Criterion | Status |
|-----------|--------|
| Problem description (2) | ✅ Documented above |
| Retrieval flow (2) | ✅ KB + LLM |
| Retrieval evaluation (2) | ✅ `eval/retrieval_eval.py` compares BM25, dense, hybrid+rerank |
| LLM evaluation (2) | ✅ `eval/llm_eval.py` judges ≥3 prompt variants |
| Interface (2) | ✅ Streamlit UI + FastAPI |
| Ingestion pipeline (2) | ✅ `dlt` automated pipeline |
| Monitoring (2) | ✅ User feedback + 6-chart dashboard |
| Containerization (2) | ✅ `docker-compose.yml` (qdrant + ingest + app + api) |
| Reproducibility (2) | ✅ Pinned `requirements.txt`, clear setup steps |
| Best practices | ✅ Hybrid search, re-ranking, query rewriting |

Run the evaluations locally:

```bash
python eval/generate_golden.py        # writes eval/golden.csv
python eval/retrieval_eval.py         # writes eval/results.retrieval.json
python eval/llm_eval.py               # writes eval/results.llm.json
```

## How to run

See [`setup.md`](setup.md) for installation and [`usage.md`](usage.md) for
day-to-day commands.

TL;DR (Docker):

```bash
cp .env.example .env          # add OPENAI_API_KEY
docker compose up qdrant app  # start Qdrant + Streamlit
docker compose --profile ingest run --rm ingest   # ingest sources
```

Open <http://localhost:8501> for the chat UI; the dashboard lives on
<http://localhost:8501/Dashboard>.

## Disclaimer

HRAI provides **general information**, not legal advice. Always confirm
specific cases with a qualified Saudi lawyer or the MHRSD.

## License

MIT for the code; each source document is used under its public license as
recorded in `data/sources.csv`.