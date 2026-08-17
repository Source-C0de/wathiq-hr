"""SQLite-backed logging for queries, retrieved chunks, and feedback.

Two tables:
  - query_logs: one row per user question (latency, lang, retrieved ids, ...)
  - feedback:   optional 0/1 rating + comment tied to a query_logs row
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("WATHIQ_DB_PATH", "monitoring/wathiq.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    lang TEXT NOT NULL,
    query TEXT NOT NULL,
    retrieved_ids TEXT,
    latency_ms INTEGER,
    answered INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,        -- +1 / -1
    comment TEXT,
    ts TEXT NOT NULL,
    FOREIGN KEY (log_id) REFERENCES query_logs(id)
);

CREATE INDEX IF NOT EXISTS idx_query_logs_ts ON query_logs(ts);
CREATE INDEX IF NOT EXISTS idx_feedback_log ON feedback(log_id);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


def log_query(
    *,
    lang: str,
    query: str,
    retrieved_ids: list[str],
    latency_ms: int,
    answered: bool,
) -> int:
    init_db()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn() as c:
        cur = c.execute(
            "INSERT INTO query_logs(ts, lang, query, retrieved_ids, latency_ms, answered) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ts, lang, query, json.dumps(retrieved_ids, ensure_ascii=False), int(latency_ms), int(answered)),
        )
        return int(cur.lastrowid)


def add_feedback(log_id: int, rating: int, comment: str | None = None) -> int:
    init_db()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn() as c:
        cur = c.execute(
            "INSERT INTO feedback(log_id, rating, comment, ts) VALUES (?, ?, ?, ?)",
            (log_id, int(rating), comment, ts),
        )
        return int(cur.lastrowid)


def fetch_metrics() -> dict:
    init_db()
    with conn() as c:
        rows = c.execute(
            "SELECT COUNT(*) AS n FROM query_logs"
        ).fetchone()
        total = rows["n"]

        rows = c.execute(
            "SELECT AVG(latency_ms) AS avg_lat FROM query_logs WHERE latency_ms IS NOT NULL"
        ).fetchone()
        avg_latency = float(rows["avg_lat"] or 0)

        rows = c.execute(
            "SELECT SUM(CASE WHEN answered=0 THEN 1 ELSE 0 END) AS u FROM query_logs"
        ).fetchone()
        unanswered = int(rows["u"] or 0)

        rows = c.execute(
            "SELECT COUNT(*) AS f FROM feedback"
        ).fetchone()
        feedback_n = int(rows["f"] or 0)

        rows = c.execute(
            "SELECT SUM(CASE WHEN rating>0 THEN 1 ELSE 0 END) AS p, "
            "SUM(CASE WHEN rating<0 THEN 1 ELSE 0 END) AS n FROM feedback"
        ).fetchone()
        thumbs_up = int(rows["p"] or 0)
        thumbs_down = int(rows["n"] or 0)

    return {
        "total_queries": total,
        "avg_latency_ms": round(avg_latency, 1),
        "unanswered": unanswered,
        "feedback_count": feedback_n,
        "thumbs_up": thumbs_up,
        "thumbs_down": thumbs_down,
    }


def daily_counts() -> list[dict]:
    init_db()
    with conn() as c:
        rows = c.execute(
            "SELECT substr(ts, 1, 10) AS day, COUNT(*) AS n "
            "FROM query_logs GROUP BY day ORDER BY day"
        ).fetchall()
    return [dict(r) for r in rows]


def language_split() -> list[dict]:
    init_db()
    with conn() as c:
        rows = c.execute(
            "SELECT lang, COUNT(*) AS n FROM query_logs GROUP BY lang"
        ).fetchall()
    return [dict(r) for r in rows]


def top_sources(retrieved_ids_all: list[list[str]], source_lookup: dict[str, str]) -> list[dict]:
    """Aggregate source frequencies across all logged retrievals."""
    counts: dict[str, int] = {}
    for ids in retrieved_ids_all:
        for cid in ids:
            src = source_lookup.get(cid, "unknown")
            counts[src] = counts.get(src, 0) + 1
    return [{"source_id": k, "n": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]