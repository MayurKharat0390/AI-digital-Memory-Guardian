# 🧠 AI Digital Memory Guardian

A fully working, end-to-end RAG (Retrieval-Augmented Generation) personal memory system.
Upload your documents, query them with natural language, and get AI-synthesized answers — powered by **local embeddings** (no API for search) + **Anthropic Claude** (for answer generation).

---

## Architecture

```
Document Upload / Pasted Text
        ↓
  Text Chunker          (paragraph-split + sliding window)
        ↓
  all-MiniLM-L6-v2      (local sentence-transformer, 384-dim real vectors)
        ↓
  ChromaDB (on-disk)    (persistent HNSW vector index at ./chroma_db/)
        ↓
  Query → Embed → Cosine NN Search → Re-rank (similarity + recency + frequency)
        ↓
  Anthropic Claude API  (real API call, RAG prompt with retrieved chunks)
        ↓
  Answer + Keyword vs. Semantic Comparison
```

---

## Prerequisites

- Python **3.10–3.12** (3.11 recommended)
- An **Anthropic API key** (get one at [console.anthropic.com](https://console.anthropic.com))
- ~1 GB disk space (for PyTorch + sentence-transformers model cache)

---

## Setup

### 1. Clone / navigate to project directory

```powershell
cd "d:\PROJECTS\ARYAN TS"
```

### 2. Create a virtual environment (recommended)

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

> **Note:** The first install downloads PyTorch (CPU build, ~700 MB) and sentence-transformers (~22 MB model).  
> Subsequent runs use local cache and start fast.

### 4. Set your Anthropic API key (optional — enables RAG answers)

**Option A — Environment variable (recommended):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-YOUR_KEY_HERE"
```

**Option B — Enter it in the Streamlit sidebar** at runtime.

> Without an API key, ingestion + semantic search still work fully. Only the Claude answer step is disabled.

---

## Running the App

```powershell
streamlit run app.py
```

The app opens at **http://localhost:8501**

---

## Quick Test Walkthrough

1. **Ingest**: Go to the **Ingest** tab → click "Browse files" → upload all three files from `sample_docs/` → click **"Embed & Store in Memory"**

2. **Query**: Go to **Query & Answer** → type one of the example queries below → click **"Search My Memory"**

3. **Compare**: Go to **Compare Modes** → use the same query to see keyword vs. semantic results side-by-side

4. **Library**: Go to **Library** to see ingested docs with retrieval statistics

### Example queries to try

| Query | What it finds |
|---|---|
| `How did the investor pitch go?` | Journal entry about Dr. Patel pitch |
| `What concerns did the team raise about the roadmap?` | Meeting notes — Sarah's pushback |
| `How did I feel eating alone in Japan?` | Travel memory about ramen in Osaka |
| `What technical infrastructure decisions were made?` | Meeting notes — ChromaDB sharding |
| `When did I feel anxious and how did I cope?` | Journal entry about anxiety + therapist |
| `What was the most peaceful moment I experienced?` | Travel memory — Fushimi Inari |

> **Tip:** The "anxious" query is a great demo — keyword search will miss it if you ask "worried" or "stressed" instead, while semantic search will still find it.

---

## Feature Checklist

| Requirement | Status | Implementation |
|---|---|---|
| Real embeddings | ✅ | `all-MiniLM-L6-v2` via sentence-transformers (local, 384-dim) |
| Real vector DB | ✅ | ChromaDB persistent client at `./chroma_db/` |
| Real ingestion pipeline | ✅ | `pipeline/chunker.py` + `pipeline/embedder.py` |
| Real semantic search | ✅ | ChromaDB cosine NN search, real similarity scores |
| Real LLM answering (RAG) | ✅ | Anthropic `messages.create()` API call |
| Comparison mode | ✅ | Side-by-side keyword TF vs. semantic + RAG |
| Importance/context re-ranking | ✅ | `similarity*0.75 + recency*0.15 + freq*0.10` |
| Working Streamlit UI | ✅ | 4 tabs: Ingest / Query / Compare / Library |
| Persistence | ✅ | ChromaDB writes to `./chroma_db/` on disk |
| Runnable locally | ✅ | `pip install -r requirements.txt && streamlit run app.py` |

---

## File Structure

```
.
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── pipeline/
│   ├── __init__.py
│   ├── chunker.py              # Text chunking (paragraph + sliding window)
│   ├── embedder.py             # Sentence-transformer embedding (local)
│   ├── vector_store.py         # ChromaDB wrapper + re-ranking
│   ├── keyword_search.py       # Naive keyword TF search (for comparison)
│   └── rag.py                  # Anthropic Claude RAG call
├── sample_docs/
│   ├── personal_journal.txt    # Sample: personal diary entries
│   ├── meeting_notes.txt       # Sample: product meeting notes
│   └── travel_memories.txt     # Sample: travel journal
└── chroma_db/                  # Created automatically on first ingest
    └── ...                     # ChromaDB persistent index files
```

---

## Re-ranking Logic

Every semantic search result is scored as:

```
final_score = (cosine_similarity × 0.75)
            + (recency_bonus × 0.15)      # normalised: recent docs score higher
            + (frequency_bonus × 0.10)    # log(retrieval_count + 1) / log(101)
```

All inputs are real metadata stored in ChromaDB and updated on every retrieval.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'pipeline'` | Run from the project root: `streamlit run app.py` |
| ChromaDB collection empty after restart | Check that `./chroma_db/` directory exists and has files |
| Claude API error `401` | Verify your API key is correct and active |
| First load is slow | Model is downloading (~22 MB) — subsequent runs use cache |
| `torch` install fails | Use Python 3.10–3.12; try `pip install torch --index-url https://download.pytorch.org/whl/cpu` |

---

## Privacy

- All embeddings are computed **locally** using a model that runs on your machine
- Documents never leave your machine for search/retrieval — only the query context goes to Anthropic for answer generation
- All data is stored in `./chroma_db/` on your local filesystem
