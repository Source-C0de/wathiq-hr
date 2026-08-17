"""Streamlit chat UI for Wathiq HR — Saudi Labour Law Assistant.

Run from the repo root:
    streamlit run app/Home.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make the project root importable when launched via `streamlit run app/Home.py`.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from app.rag import Answer, answer_question, answer_question_stream  # noqa: E402
from monitoring import db as mdb  # noqa: E402

load_dotenv()
mdb.init_db()

st.set_page_config(
    page_title="Wathiq HR — Saudi Labour Law Assistant",
    page_icon="WH",
    layout="wide",
)

# --- Sidebar ---------------------------------------------------------------
with st.sidebar:
    st.markdown("## Wathiq HR")
    st.caption("Saudi Labour Law · HR · Employee Rights")
    lang = st.selectbox("Language / اللغة", options=["en", "ar"], index=0)
    top_k = st.slider("Top-k passages", min_value=3, max_value=10, value=5)
    use_rerank = st.checkbox("Re-rank passages (cross-encoder)", value=True)
    # Rewriter is OFF by default — it adds a full OpenAI round-trip before
    # retrieval. Most queries are handled well by the BM25+dense hybrid path.
    use_rewriter = st.checkbox("Rewrite query before retrieval", value=False)
    st.divider()
    st.markdown("**Example questions**")
    examples_en = [
        "How many days of annual leave am I entitled to?",
        "What is the notice period during probation?",
        "How is end-of-service benefit (EOSB) calculated?",
        "Am I allowed to work remotely under Saudi law?",
        "What does WPS (Wage Protection System) require from employers?",
    ]
    for ex in examples_en:
        if st.button(ex, key=f"ex_{ex[:24]}"):
            st.session_state.setdefault("pending", []).append(ex)

# --- Header ----------------------------------------------------------------
st.title("Wathiq HR — Saudi Labour Law Assistant")
st.write(
    "Ask plain-language questions about the Saudi Labour Law, HR policy, "
    "and employee rights. Answers are grounded in official sources and "
    "cite the supporting article when available. *Not legal advice.*"
)

# --- Chat state ------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []  # list[dict(role, content, citations, log_id)]
if "pending" not in st.session_state:
    st.session_state["pending"] = []

# Drain pending example clicks into the prompt box.
if st.session_state["pending"]:
    st.session_state["draft"] = st.session_state["pending"].pop(0)

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("citations"):
            with st.expander("Citations & sources"):
                for c in msg["citations"]:
                    st.markdown(
                        f"- **{c['source_id']}**"
                        + (f", Article {c['article_no']}" if c.get("article_no") else "")
                        + f" — [{c['url']}]({c['url']})"
                    )
                    st.caption(c["text"][:240] + ("…" if len(c["text"]) > 240 else ""))
        if msg["role"] == "assistant" and msg.get("log_id"):
            cols = st.columns(2)
            with cols[0]:
                if st.button("Helpful", key=f"up_{msg['log_id']}"):
                    mdb.add_feedback(msg["log_id"], +1)
                    st.success("Thanks for the feedback!")
            with cols[1]:
                if st.button("Not helpful", key=f"dn_{msg['log_id']}"):
                    mdb.add_feedback(msg["log_id"], -1)
                    st.info("Feedback recorded.")

# --- Input -----------------------------------------------------------------
prompt = st.chat_input("Ask a question (English or العربية)…") or st.session_state.pop("draft", None)

if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Stream tokens as they arrive. The stream yields text chunks first,
        # then a final (Answer, latency_ms, first_token_ms) tuple.
        with st.status("Searching the law…", expanded=False) as status:
            stream = answer_question_stream(
                prompt,
                language=lang,
                top_k=top_k,
                use_rewriter=use_rewriter,
                use_rerank=use_rerank,
            )
            text_holder = st.empty()
            full_text_parts: list[str] = []
            ans = None
            for item in stream:
                if isinstance(item, str):
                    full_text_parts.append(item)
                    text_holder.write("".join(full_text_parts))
                else:
                    ans, _latency_ms, _first_token_ms = item
            if ans is None:
                # Defensive fallback if the stream yielded nothing.
                ans = answer_question(
                    prompt,
                    language=lang,
                    top_k=top_k,
                    use_rewriter=use_rewriter,
                    use_rerank=use_rerank,
                )
            status.update(label="Done", state="complete")

        if ans.citations:
            with st.expander("Citations & sources"):
                for c in ans.citations:
                    st.markdown(
                        f"- **{c.source_id}**"
                        + (f", Article {c.article_no}" if c.article_no else "")
                        + f" — [{c.url}]({c.url})"
                    )
                    st.caption(c.text[:240] + ("…" if len(c.text) > 240 else ""))

        log_id = mdb.log_query(
            lang=lang,
            query=prompt,
            retrieved_ids=ans.retrieved_ids,
            latency_ms=ans.latency_ms,
            answered=ans.answered,
        )

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": ans.text,
            "citations": [
                {
                    "source_id": c.source_id,
                    "article_no": c.article_no,
                    "url": c.url,
                    "text": c.text,
                }
                for c in ans.citations
            ],
            "log_id": log_id,
        }
    )
