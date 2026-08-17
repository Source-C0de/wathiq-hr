# Usage

## Streamlit chat

```bash
streamlit run app/Home.py
```

Then open <http://localhost:8501>.

- **Sidebar**: choose language (English/العربية), tune `top_k`, toggle the
  reranker and the query rewriter.
- **Example questions**: click any preset to pre-fill the input box.
- **Feedback**: each assistant answer has 👍 / 👎 buttons; comments live on
  the **Feedback** page.
- **Dashboard**: navigate to the **Dashboard** page to see 6 charts updated
  live from the SQLite logs.

## FastAPI

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

```bash
curl -X POST http://localhost:8000/ask \
  -H 'content-type: application/json' \
  -d '{"query": "How many days of annual leave am I entitled to?", "language": "en"}'
```

Response shape:

```json
{
  "answer": "Under the Saudi Labour Law, you are entitled to ...",
  "citations": [{"source_id": "m51_en", "article_no": "109", "url": "...", "text": "..."}],
  "latency_ms": 845,
  "language": "en"
}
```

## Ingestion

```bash
# Full re-ingest (drops the Qdrant collection first)
python ingest/run_pipeline.py --reset

# Smoke test on the first 200 chunks
python ingest/run_pipeline.py --reset --limit 200
```

## Evaluation

```bash
# Write the golden Q&A file
python eval/generate_golden.py

# Compare BM25 vs dense vs hybrid+rerank (hit-rate, MRR)
python eval/retrieval_eval.py

# Compare prompt variants via LLM-as-judge
python eval/llm_eval.py
```

Both scripts print a small leaderboard and write JSON results to
`eval/results.retrieval.json` / `eval/results.llm.json`.

## Monitoring data

- Queries land in `monitoring/wathiq.db` (table `query_logs`).
- Feedback rows land in the `feedback` table.
- Delete the file to reset all metrics.

## Cloud deploy (bonus)

The `app` service is a stock Streamlit container and can be deployed to
Render, Fly.io, or Hugging Face Spaces with minimal changes. See
[`docs/deploy.md`](docs/deploy.md) (TODO) for a step-by-step guide.