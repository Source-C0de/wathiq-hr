# syntax=docker/dockerfile:1.6
# Wathiq HR – image used by app, api, and ingest services.
# Pinned base: python 3.11 (matches requirements.txt).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TRANSFORMERS_NO_ADVISORY_WARNINGS=1

WORKDIR /app

# OS deps for pypdf + lxml + curl-based health checks.
# libgomp1 is required by onnxruntime (fastembed dep).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer cache.
COPY requirements.txt .
# --upgrade-strategy only-if-needed avoids inadvertently bumping pinned versions.
RUN pip install --upgrade pip \
    && pip install --upgrade-strategy only-if-needed -r requirements.txt

# Copy the rest of the source.
COPY . .

# Streamlit must bind to 0.0.0.0 inside the container.
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501 8000

# Run as non-root for safety.
RUN useradd --create-home --uid 1000 wathiq \
    && chown -R wathiq:wathiq /app
USER wathiq

# Default = chat UI. Override in docker-compose for the API / ingest services.
CMD ["streamlit", "run", "app/Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
