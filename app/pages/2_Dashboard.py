"""Monitoring dashboard with >=5 charts powered by SQLite query/feedback logs."""
from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from monitoring import db as mdb  # noqa: E402

st.set_page_config(page_title="Dashboard · HRAI", page_icon="📊", layout="wide")
mdb.init_db()

st.title("📊 Monitoring dashboard")

metrics = mdb.fetch_metrics()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total questions", metrics["total_queries"])
c2.metric("Avg latency (ms)", metrics["avg_latency_ms"])
c3.metric("Unanswered", metrics["unanswered"])
c4.metric("Feedback count", metrics["feedback_count"])

st.divider()

# 1) Daily question volume (line chart)
daily = pd.DataFrame(mdb.daily_counts())
if not daily.empty:
    st.subheader("1. Questions per day")
    st.altair_chart(
        alt.Chart(daily).mark_line(point=True).encode(x="day:T", y="n:Q"),
        use_container_width=True,
    )
else:
    st.info("No questions logged yet.")

# 2) Language split (pie/donut)
lang_df = pd.DataFrame(mdb.language_split())
if not lang_df.empty:
    st.subheader("2. Language split")
    st.altair_chart(
        alt.Chart(lang_df).mark_arc(innerRadius=60).encode(theta="n:Q", color="lang:N"),
        use_container_width=True,
    )

# 3) Latency distribution (histogram)
with mdb.conn() as c:
    lat_rows = c.execute(
        "SELECT latency_ms FROM query_logs WHERE latency_ms IS NOT NULL"
    ).fetchall()
if lat_rows:
    lat_df = pd.DataFrame([dict(r) for r in lat_rows])
    st.subheader("3. Latency distribution (ms)")
    st.altair_chart(
        alt.Chart(lat_df).mark_bar().encode(
            x=alt.X("latency_ms:Q", bin=alt.Bin(maxbins=20)),
            y="count():Q",
        ),
        use_container_width=True,
    )

# 4) Thumbs up vs down (bar)
fb_df = pd.DataFrame(
    [
        {"rating": "👍", "n": metrics["thumbs_up"]},
        {"rating": "👎", "n": metrics["thumbs_down"]},
    ]
)
st.subheader("4. Feedback ratio")
st.altair_chart(
    alt.Chart(fb_df).mark_bar().encode(x="rating:N", y="n:Q", color="rating:N"),
    use_container_width=True,
)

# 5) Top retrieved sources (bar)
with mdb.conn() as c:
    src_rows = c.execute("SELECT retrieved_ids FROM query_logs WHERE retrieved_ids IS NOT NULL").fetchall()
if src_rows:
    import json

    from retrieval.store import fetch_all_chunks

    try:
        chunks = fetch_all_chunks()
        lookup = {c.chunk_id: c.source_id for c in chunks}
    except Exception:
        lookup = {}

    ids_lists = [json.loads(r["retrieved_ids"]) for r in src_rows]
    agg: dict[str, int] = {}
    for ids in ids_lists:
        for cid in ids:
            agg[lookup.get(cid, "unknown")] = agg.get(lookup.get(cid, "unknown"), 0) + 1
    src_df = pd.DataFrame(
        [{"source_id": k, "n": v} for k, v in sorted(agg.items(), key=lambda x: -x[1])[:10]]
    )
    st.subheader("5. Top cited sources")
    st.altair_chart(
        alt.Chart(src_df).mark_bar().encode(x="n:Q", y=alt.Y("source_id:N", sort="-x")),
        use_container_width=True,
    )

# 6) Unanswered rate over time
with mdb.conn() as c:
    rate_rows = c.execute(
        "SELECT substr(ts,1,10) AS day, "
        "SUM(CASE WHEN answered=0 THEN 1 ELSE 0 END) AS unanswered, "
        "COUNT(*) AS total FROM query_logs GROUP BY day ORDER BY day"
    ).fetchall()
if rate_rows:
    rate_df = pd.DataFrame([dict(r) for r in rate_rows])
    rate_df["rate"] = rate_df["unanswered"] / rate_df["total"]
    st.subheader("6. Unanswered rate over time")
    st.altair_chart(
        alt.Chart(rate_df).mark_line(point=True).encode(x="day:T", y="rate:Q"),
        use_container_width=True,
    )

st.caption(
    "Charts regenerate from `monitoring/hrai.db` on each reload. Logs are "
    "written by the Streamlit chat UI and the FastAPI service."
)