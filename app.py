"""
app.py
------
AI Digital Memory Guardian — Main Streamlit Application

Full pipeline:
  Upload/Paste → Chunk → Embed (local) → Store (ChromaDB on disk)
  Query → Embed → Semantic Search → Re-rank → RAG (Claude API) → Answer

Also shows:
  - Keyword search vs. semantic search comparison
  - Document library with retrieval stats
  - All real computations — no mocks, no stubs
"""

import os
import time
import datetime

import streamlit as st
from sentence_transformers import SentenceTransformer

# ── Internal pipeline modules ─────────────────────────────────────────────────
from pipeline.chunker       import chunk_text
from pipeline.embedder      import embed_texts, embed_query
from pipeline.vector_store  import (
    add_documents, semantic_search, update_retrieval_stats,
    list_sources, delete_source, collection_count,
)
from pipeline.keyword_search import keyword_search
from pipeline.rag            import generate_answer, DEFAULT_MODEL

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Digital Memory Guardian",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Dark gradient background */
  .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255,255,255,0.08);
  }

  /* Cards */
  .memory-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    backdrop-filter: blur(8px);
    transition: border-color 0.2s;
  }
  .memory-card:hover { border-color: rgba(138,43,226,0.6); }

  /* Score badges */
  .badge-semantic {
    background: linear-gradient(90deg, #7928ca, #ff0080);
    color: white; padding: 3px 10px; border-radius: 20px;
    font-size: 0.78em; font-weight: 600;
  }
  .badge-keyword {
    background: linear-gradient(90deg, #f7971e, #ffd200);
    color: #1a1a1a; padding: 3px 10px; border-radius: 20px;
    font-size: 0.78em; font-weight: 600;
  }
  .badge-source {
    background: rgba(255,255,255,0.15);
    color: #ccc; padding: 3px 10px; border-radius: 20px;
    font-size: 0.75em;
  }

  /* Comparison columns */
  .col-semantic { border-left: 3px solid #7928ca; padding-left: 12px; }
  .col-keyword  { border-left: 3px solid #f7971e; padding-left: 12px; }

  /* Answer box */
  .answer-box {
    background: linear-gradient(135deg, rgba(121,40,202,0.15), rgba(255,0,128,0.10));
    border: 1px solid rgba(121,40,202,0.4);
    border-radius: 14px;
    padding: 20px 24px;
    margin-top: 16px;
  }

  /* Metric tiles */
  [data-testid="stMetric"] {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 10px 16px;
    border: 1px solid rgba(255,255,255,0.08);
  }

  h1, h2, h3 { color: #f0f0f0 !important; }
  p, li, label { color: #c8c8d0 !important; }
  .stTextInput input, .stTextArea textarea {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #f0f0f0 !important;
    border-radius: 8px !important;
  }
  .stButton > button {
    background: linear-gradient(90deg, #7928ca, #ff0080) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    transition: opacity 0.2s !important;
  }
  .stButton > button:hover { opacity: 0.85 !important; }
  .stTabs [data-baseweb="tab"] { color: #aaa !important; }
  .stTabs [aria-selected="true"] { color: #ff79c6 !important; border-bottom-color: #ff79c6 !important; }
</style>
""", unsafe_allow_html=True)


# ── Cached model loader (loads once per Streamlit session) ─────────────────────
@st.cache_resource(show_spinner="🔄 Loading embedding model (first run only)…")
def load_embedding_model() -> SentenceTransformer:
    """Load all-MiniLM-L6-v2 locally — 384-dim real vectors."""
    return SentenceTransformer("all-MiniLM-L6-v2")


# ── Helper: format timestamp ──────────────────────────────────────────────────
def _fmt_ts(ts: float) -> str:
    if not ts:
        return "never"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🧠 Memory Guardian")
    st.markdown("---")

    # Anthropic API key
    st.markdown("### 🔑 API Configuration")
    api_key_input = st.text_input(
        "Anthropic API Key",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Required for RAG answer generation. Get yours at console.anthropic.com",
        placeholder="sk-ant-…",
    )
    api_key = api_key_input.strip() or None

    # Model selector
    model_choice = st.selectbox(
        "Claude Model",
        options=[
            "claude-3-5-haiku-20241022",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
        ],
        index=0,
        help="Haiku = fastest & cheapest. Sonnet = balanced. Opus = most capable.",
    )

    st.markdown("---")

    # DB Stats
    st.markdown("### 📊 Knowledge Base")
    total_chunks = collection_count()
    sources      = list_sources()
    col1, col2 = st.columns(2)
    col1.metric("Chunks", total_chunks)
    col2.metric("Documents", len(sources))

    if sources:
        st.markdown("**Ingested Sources:**")
        for s in sources:
            st.markdown(
                f"- `{s['source']}` — {s['chunk_count']} chunks, "
                f"retrieved {s['total_retrieved']}×"
            )

    st.markdown("---")
    st.markdown("### ⚙️ About")
    st.markdown(
        "**Embedding**: `all-MiniLM-L6-v2` (local, 384-dim)  \n"
        "**Vector DB**: ChromaDB (on-disk, persistent)  \n"
        "**LLM**: Anthropic Claude (real API call)  \n"
        "**Re-ranking**: similarity × 0.75 + recency × 0.15 + freq × 0.10"
    )

# ── Load model ────────────────────────────────────────────────────────────────
model = load_embedding_model()

# ── Main header ───────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center; background: linear-gradient(90deg,#7928ca,#ff0080);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
    "font-size:2.6em; margin-bottom:4px;'>🧠 AI Digital Memory Guardian</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center; color:#888; margin-bottom:24px;'>"
    "Ingest your documents • Semantic memory retrieval • RAG-powered answers</p>",
    unsafe_allow_html=True
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_ingest, tab_query, tab_compare, tab_library = st.tabs([
    "📥 Ingest",
    "🔍 Query & Answer",
    "⚖️ Compare Modes",
    "📚 Library",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — INGEST
# ══════════════════════════════════════════════════════════════════════════════
with tab_ingest:
    st.markdown("## 📥 Ingest Documents into Memory")
    st.markdown(
        "Upload `.txt` or `.md` files, or paste text directly. "
        "Each document is chunked, embedded with a local model, "
        "and stored in ChromaDB on disk."
    )

    ingest_mode = st.radio(
        "Input method",
        ["Upload File(s)", "Paste Text"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if ingest_mode == "Upload File(s)":
        uploaded_files = st.file_uploader(
            "Drop .txt or .md files here",
            type=["txt", "md"],
            accept_multiple_files=True,
        )
        texts_to_ingest: list[tuple[str, str]] = []  # (source_name, text)
        if uploaded_files:
            for f in uploaded_files:
                raw = f.read().decode("utf-8", errors="replace")
                texts_to_ingest.append((f.name, raw))
                st.success(f"✅ Loaded: `{f.name}` ({len(raw):,} chars)")
    else:
        paste_name = st.text_input("Document name / tag", value="pasted_text", max_chars=80)
        paste_text = st.text_area("Paste your text here", height=250)
        texts_to_ingest = [(paste_name, paste_text)] if paste_text.strip() else []

    # ── Chunking preview ──────────────────────────────────────────────────────
    if texts_to_ingest:
        if st.toggle("👁️ Preview chunks before ingesting"):
            preview_name, preview_text = texts_to_ingest[0]
            preview_chunks = chunk_text(preview_text)
            st.markdown(
                f"**`{preview_name}`** → **{len(preview_chunks)} chunks** "
                f"(showing first 5)"
            )
            for i, ch in enumerate(preview_chunks[:5]):
                with st.expander(f"Chunk {i} — {len(ch['text'])} chars"):
                    st.text(ch["text"])

    # ── Ingest button ─────────────────────────────────────────────────────────
    if texts_to_ingest and st.button("⚡ Embed & Store in Memory", use_container_width=True):
        total_added = 0
        progress = st.progress(0, text="Starting ingestion…")

        for file_idx, (source_name, raw_text) in enumerate(texts_to_ingest):
            prog_frac_start = file_idx / len(texts_to_ingest)

            # Stage 1: Chunk
            progress.progress(prog_frac_start, text=f"✂️ Chunking `{source_name}`…")
            chunks = chunk_text(raw_text)
            if not chunks:
                st.warning(f"No content found in `{source_name}` — skipped.")
                continue

            # Stage 2: Embed (real local model)
            progress.progress(
                prog_frac_start + 0.3 / len(texts_to_ingest),
                text=f"🔢 Embedding {len(chunks)} chunks from `{source_name}`…"
            )
            chunk_texts_list = [c["text"] for c in chunks]
            embeddings = embed_texts(chunk_texts_list, model=model)

            # Stage 3: Store in ChromaDB
            progress.progress(
                prog_frac_start + 0.6 / len(texts_to_ingest),
                text=f"💾 Storing in ChromaDB…"
            )
            n_added = add_documents(
                chunks=chunks,
                embeddings=[e.tolist() for e in embeddings],
                source=source_name,
                upload_ts=time.time(),
            )
            total_added += n_added

        progress.progress(1.0, text="✅ Ingestion complete!")
        st.balloons()
        st.success(
            f"Stored **{total_added} chunks** across {len(texts_to_ingest)} document(s). "
            f"Total in DB: **{collection_count()}** chunks."
        )
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — QUERY & ANSWER
# ══════════════════════════════════════════════════════════════════════════════
with tab_query:
    st.markdown("## 🔍 Query Your Memory")

    if collection_count() == 0:
        st.info("⬅️ No memories yet. Go to **Ingest** to add documents first.")
    else:
        query_text = st.text_input(
            "Ask a question about your documents…",
            placeholder="e.g. What did I think about the product launch?",
            key="main_query",
        )

        top_k_slider = st.slider("Top-K results to retrieve", 1, 10, 5, key="query_topk")

        run_rag = st.checkbox(
            "Generate RAG answer with Claude",
            value=True,
            help="Requires a valid Anthropic API key in the sidebar.",
        )

    if query_text and st.button("🔍 Search My Memory", use_container_width=True, key="btn_query"):

        # ── Stage 1: Embed query ──────────────────────────────────────────────
        with st.spinner("🔢 Embedding query…"):
            q_vec = embed_query(query_text, model=model)

        # ── Stage 2: Semantic search in ChromaDB ──────────────────────────────
        with st.spinner("🔎 Searching ChromaDB…"):
            results = semantic_search(q_vec, top_k=top_k_slider)

        if not results:
            st.warning("No matching memories found.")
        else:
            # Update retrieval stats for returned chunks
            update_retrieval_stats([r["id"] for r in results])

            st.markdown(f"### 🎯 Top {len(results)} Semantic Results")
            for i, r in enumerate(results, 1):
                meta = r["metadata"]
                with st.container():
                    st.markdown(
                        f"""<div class='memory-card'>
                        <span class='badge-semantic'>Relevance: {r['final_score']:.3f}</span>&nbsp;
                        <span class='badge-source'>📄 {meta.get('source','?')}</span>&nbsp;
                        <span class='badge-source'>Chunk #{meta.get('chunk_index','?')}</span>&nbsp;
                        <span style='font-size:0.75em; color:#888;'>
                          Retrieved {int(meta.get('retrieval_count',0))}× before
                        </span>
                        <hr style='border-color:rgba(255,255,255,0.08); margin:10px 0;'>
                        <p style='margin:0; color:#e0e0e0; line-height:1.6;'>{r['text']}</p>
                        <p style='margin:6px 0 0; font-size:0.75em; color:#666;'>
                          similarity={r['similarity']:.4f} | recency={r['recency']:.4f} | freq={r['frequency']:.4f}
                        </p>
                        </div>""",
                        unsafe_allow_html=True
                    )

            # ── Stage 3: RAG with Claude ──────────────────────────────────────
            if run_rag:
                if not api_key:
                    st.warning("⚠️ Add your Anthropic API key in the sidebar to generate an answer.")
                else:
                    st.markdown("### 💬 AI Answer (RAG via Claude)")
                    with st.spinner("🤖 Generating answer with Claude…"):
                        try:
                            answer, usage = generate_answer(
                                query=query_text,
                                chunks=results,
                                api_key=api_key,
                                model=model_choice,
                            )
                            st.markdown(
                                f"<div class='answer-box'>{answer}</div>",
                                unsafe_allow_html=True
                            )
                            st.markdown(
                                f"<p style='font-size:0.75em; color:#666; margin-top:8px;'>"
                                f"Model: {usage['model']} | "
                                f"Tokens: {usage['input_tokens']} in / {usage['output_tokens']} out"
                                f"</p>",
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.error(f"Claude API error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARISON MODE
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("## ⚖️ Keyword Search vs. Semantic Search")
    st.markdown(
        "Run the **same query** through both methods simultaneously "
        "to see why semantic/vector search outperforms naive keyword matching."
    )

    if collection_count() == 0:
        st.info("⬅️ No memories yet. Go to **Ingest** to add documents first.")
    else:
        cmp_query = st.text_input(
            "Enter your comparison query",
            placeholder="e.g. How was my performance review received?",
            key="cmp_query",
        )
        cmp_k = st.slider("Top-K", 1, 10, 5, key="cmp_topk")

        if cmp_query and st.button("⚖️ Run Comparison", use_container_width=True, key="btn_compare"):

            # Keyword search
            with st.spinner("Running keyword search…"):
                kw_results = keyword_search(cmp_query, top_k=cmp_k)

            # Semantic search
            with st.spinner("Running semantic search…"):
                q_vec       = embed_query(cmp_query, model=model)
                sem_results = semantic_search(q_vec, top_k=cmp_k)
                if sem_results:
                    update_retrieval_stats([r["id"] for r in sem_results])

            # Side-by-side display
            col_kw, col_sem = st.columns(2)

            with col_kw:
                st.markdown(
                    "<div class='col-keyword'>"
                    "<h3 style='color:#ffd200;'>🔤 Keyword Search</h3>"
                    "<p style='font-size:0.85em; color:#999;'>Simple term-frequency matching — no semantics</p>"
                    "</div>",
                    unsafe_allow_html=True
                )
                if not kw_results:
                    st.info("No keyword matches found.")
                else:
                    for r in kw_results:
                        terms = ", ".join(r["matched_terms"]) if r["matched_terms"] else "none"
                        st.markdown(
                            f"""<div class='memory-card'>
                            <span class='badge-keyword'>Score: {r['kw_score']:.3f}</span>&nbsp;
                            <span class='badge-source'>📄 {r['metadata'].get('source','?')}</span>
                            <p style='font-size:0.78em; color:#888; margin:6px 0;'>
                              Matched terms: <em>{terms}</em>
                            </p>
                            <hr style='border-color:rgba(255,255,255,0.08); margin:8px 0;'>
                            <p style='margin:0; color:#ddd; font-size:0.9em; line-height:1.5;'>{r['text'][:400]}{'…' if len(r['text'])>400 else ''}</p>
                            </div>""",
                            unsafe_allow_html=True
                        )

            with col_sem:
                st.markdown(
                    "<div class='col-semantic'>"
                    "<h3 style='color:#c084fc;'>🧠 Semantic Search + RAG</h3>"
                    "<p style='font-size:0.85em; color:#999;'>Real embeddings + cosine similarity + re-ranking</p>"
                    "</div>",
                    unsafe_allow_html=True
                )
                if not sem_results:
                    st.info("No semantic matches found.")
                else:
                    for r in sem_results:
                        st.markdown(
                            f"""<div class='memory-card'>
                            <span class='badge-semantic'>Score: {r['final_score']:.3f}</span>&nbsp;
                            <span class='badge-source'>📄 {r['metadata'].get('source','?')}</span>
                            <hr style='border-color:rgba(255,255,255,0.08); margin:8px 0;'>
                            <p style='margin:0; color:#ddd; font-size:0.9em; line-height:1.5;'>{r['text'][:400]}{'…' if len(r['text'])>400 else ''}</p>
                            </div>""",
                            unsafe_allow_html=True
                        )

                    # RAG answer in comparison mode
                    if api_key:
                        st.markdown("---")
                        st.markdown("**🤖 Claude's Answer (based on semantic results)**")
                        with st.spinner("Generating answer…"):
                            try:
                                ans, _ = generate_answer(
                                    query=cmp_query,
                                    chunks=sem_results,
                                    api_key=api_key,
                                    model=model_choice,
                                )
                                st.markdown(
                                    f"<div class='answer-box' style='font-size:0.9em;'>{ans}</div>",
                                    unsafe_allow_html=True
                                )
                            except Exception as e:
                                st.error(f"Claude error: {e}")
                    else:
                        st.caption("Add API key to sidebar to see RAG answer here.")

            # Explanation callout
            st.markdown("---")
            st.info(
                "**Why the results differ:** Keyword search only matches documents that contain "
                "the exact words in your query. Semantic search understands *meaning*, so it can "
                "find relevant passages even when they use different vocabulary to describe the same concept."
            )



# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
with tab_library:
    st.markdown("## 📚 Memory Library")
    st.markdown("All documents in your persistent ChromaDB knowledge base.")

    sources = list_sources()

    if not sources:
        st.info("No documents ingested yet. Go to the **Ingest** tab to add files.")
    else:
        # Sort by upload time (most recent first)
        sources.sort(key=lambda s: s["upload_ts"], reverse=True)

        for s in sources:
            with st.expander(f"📄 {s['source']} — {s['chunk_count']} chunks"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Chunks", s["chunk_count"])
                c2.metric("Times Retrieved", s["total_retrieved"])
                c3.metric("Uploaded", _fmt_ts(s["upload_ts"]))

                if st.button(
                    f"🗑️ Delete `{s['source']}`",
                    key=f"del_{s['source']}",
                    type="secondary",
                ):
                    n = delete_source(s["source"])
                    st.success(f"Deleted {n} chunks from `{s['source']}`.")
                    st.rerun()

    st.markdown("---")
    st.markdown(f"**Total chunks in ChromaDB:** `{collection_count()}`")
    st.markdown(f"**DB path:** `./chroma_db/` (persists across restarts)")
