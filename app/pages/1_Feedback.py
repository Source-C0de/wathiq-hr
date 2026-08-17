"""Free-text feedback page — collectors can leave comments on past answers."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from monitoring import db as mdb  # noqa: E402

st.set_page_config(page_title="Feedback · Wathiq HR", page_icon="WH", layout="wide")
mdb.init_db()

st.title("Feedback")
st.write(
    "Rate recent answers and add comments. This data drives the monitoring "
    "dashboard and helps us improve retrieval quality."
)

with mdb.conn() as c:
    rows = c.execute(
        "SELECT id, ts, lang, query, latency_ms, answered FROM query_logs "
        "ORDER BY id DESC LIMIT 50"
    ).fetchall()

if not rows:
    st.info("No questions have been logged yet. Try the chat first.")
else:
    for r in rows:
        with st.container(border=True):
            st.markdown(f"**#{r['id']} · {r['ts']} · `{r['lang']}`**")
            st.write(r["query"])
            st.caption(f"Latency: {r['latency_ms']} ms · answered={bool(r['answered'])}")
            with mdb.conn() as c:
                existing = c.execute(
                    "SELECT rating, comment FROM feedback WHERE log_id=? ORDER BY id DESC LIMIT 1",
                    (r["id"],),
                ).fetchone()
            if existing:
                label = "Helpful" if existing["rating"] > 0 else "Not helpful"
                note = f" — _{existing['comment']}_" if existing["comment"] else ""
                st.success(f"Recorded: {label}{note}")
            else:
                cols = st.columns([1, 4, 1])
                with cols[0]:
                    rating = st.radio(
                        "Rating",
                        ["Helpful", "Not helpful"],
                        key=f"r_{r['id']}",
                        horizontal=True,
                    )
                with cols[1]:
                    comment = st.text_input("Comment (optional)", key=f"c_{r['id']}")
                with cols[2]:
                    if st.button("Save", key=f"s_{r['id']}"):
                        mdb.add_feedback(r["id"], +1 if rating == "Helpful" else -1, comment or None)
                        st.success("Saved.")
