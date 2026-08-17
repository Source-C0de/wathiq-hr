# Setup

## Prerequisites

- Python **3.11**
- Docker + Docker Compose (recommended)
- An OpenAI API key with access to `text-embedding-3-small` and `gpt-4o-mini`

## Option A — Docker (recommended)

```bash
# 1. Clone and enter the repo
git clone https://github.com/<you>/hrai-saudi-labour-law-assistant.git
cd hrai-saudi-labour-law-assistant

# 2. Configure secrets
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...

# 3. Start Qdrant + Streamlit
docker compose up -d qdrant app

# 4. Ingest the law sources (one-shot)
docker compose --profile ingest run --rm ingest
```

Open <http://localhost:8501> for the chat and
<http://localhost:8501/Dashboard> for the monitoring dashboard.

## Option B — Local Python

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Qdrant (Docker)
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant:v1.12.0

# 4. Configure secrets
cp .env.example .env
# edit .env

# 5. Download raw data (or place files manually)
python ingest/download_sources.py

# 6. Run ingestion
python ingest/run_pipeline.py --reset

# 7. Launch the UI
streamlit run app/Home.py
```

## Verifying the install

```bash
# Health check
curl http://localhost:6333/healthz

# Smoke test retrieval
python -c "from retrieval.hybrid import hybrid_search as h; print(h('How many days of annual leave?', top_k=3)[0]['text'][:120])"
```

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | **Required** | – |
| `OPENAI_EMBED_MODEL` | Embedding model | `text-embedding-3-small` |
| `OPENAI_LLM_MODEL` | LLM model | `gpt-4o-mini` |
| `QDRANT_HOST` | Qdrant host | `localhost` |
| `QDRANT_PORT` | Qdrant port | `6333` |
| `QDRANT_COLLECTION` | Collection name | `hrai_saudi_labour_law` |
| `EMBED_BATCH_SIZE` | Embedding batch size | `32` |
| `HRAI_DB_PATH` | SQLite log path | `monitoring/hrai.db` |

## Troubleshooting

- **`404 page not found` on Qdrant** — the collection doesn't exist yet; run
  the ingest step.
- **`openai.error.AuthenticationError`** — `OPENAI_API_KEY` missing or wrong.
- **Empty retrievals** — the chunks were indexed but in a different
  collection. Check `QDRANT_COLLECTION`.