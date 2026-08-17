# Docker setup

This folder defines how to run HRAI end-to-end with Docker Compose.

## Services

| Service | Purpose                     | Default port |
|---------|-----------------------------|--------------|
| qdrant  | Vector database             | 6333         |
| ingest  | One-shot dlt ingestion job  | -            |
| api     | FastAPI RAG endpoint        | 8000         |
| app     | Streamlit UI + dashboard    | 8501         |

## Common commands

```bash
# 1) Bring up Qdrant + Streamlit UI
docker compose up qdrant app

# 2) Ingest the data into Qdrant
docker compose --profile ingest run --rm ingest

# 3) (Optional) Run the API
docker compose --profile api up api

# 4) Run evaluation
docker compose run --rm app python eval/retrieval_eval.py
docker compose run --rm app python eval/llm_eval.py
```

The `app` and `api` services share the `monitoring/` folder so logs persist
on the host. Qdrant state is held in the named volume `qdrant_data`.