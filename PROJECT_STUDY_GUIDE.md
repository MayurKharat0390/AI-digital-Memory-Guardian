# AI Digital Memory Guardian — Project Architecture & Study Guide

> **A local-first, privacy-preserving AI personal memory retrieval and synthesis system powered by dense vector embeddings, ChromaDB, and hybrid RAG synthesis.**

---

## 1. Executive Summary & Purpose

### What is the "AI Digital Memory Guardian"?
Human memory decays over time, and notes scattered across files are difficult to recall using traditional keyword search. Traditional search fails when you don't remember the *exact words* you used.

**AI Digital Memory Guardian** is a personal intelligence system that ingests personal journals, meeting notes, research, and reflections. It allows users to ask natural-language questions (e.g., *"When did I feel overwhelmed and how did I cope?"*) and retrieves the exact relevant memories based on **semantic meaning**, re-ranks them based on **recency and frequency**, and synthesizes an intelligent answer.

### Core Design Philosophy
* **100% Local-First Foundation:** Document chunking, vector embedding generation, vector storage, and re-ranking execute locally on your device with **zero cloud dependencies** and **zero API costs**.
* **Privacy & Security:** Sensitive personal reflections and notes do not leave your computer for storage or indexing.
* **Hybrid Synthesis:** Supports cloud generative AI (Claude 3.5) when API keys are available, with an automatic, built-in **Local Extractive Synthesis Engine** when working offline or without API credits.
* **Modern Decoupled Architecture:** Clean **Django 5 + Django REST Framework** backend powering a responsive, dark-mode single page application (**HTML5 + Tailwind CSS + Vanilla JS** with zero emojis and crisp SVG icons).

---

## 2. Technology Stack & Key Libraries

| Layer | Technology | Role & Purpose |
|---|---|---|
| **Backend Framework** | **Django 5.1 + DRF** | RESTful API endpoints, request validation, static file serving, and CORS management. |
| **Frontend UI** | **HTML5 + Tailwind CSS + Vanilla JS** | Fast, modern dark-mode SPA, responsive sidebar navigation, drag-and-drop file ingestion, dynamic source filtering, and toast feedback. |
| **Embedding Model** | **`sentence-transformers` (`all-MiniLM-L6-v2`)** | 384-dimensional local dense vector model running on PyTorch/CPU. Free, fast (~15ms/chunk), and 100% offline. |
| **Vector Database** | **ChromaDB** | Local persistent vector repository using SQLite and HNSW indexing (`data/chroma_db`). |
| **Keyword Engine** | **Custom TF-IDF Tokenizer** | Term-frequency baseline used in the Compare Search tab to demonstrate vector superiority. |
| **Synthesis Engine** | **Anthropic Claude 3.5 + Local Extractive Fallback** | Multi-engine RAG: Generates conversational answers or extracts high-relevance citations without external calls. |

---

## 3. High-Level System Architecture

```
                                  USER INTERFACE
                (HTML5 + Tailwind CSS + Vanilla JS Single Page App)
                                        │
                       HTTP REST API Calls (JSON / FormData)
                                        ▼
                               DJANGO BACKEND
                      (Django 5 + Django REST Framework)
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
   /api/ingest/                    /api/query/                 /api/compare/
(Ingestion Pipeline)          (Semantic Search & RAG)        (Search Benchmark)
           │                            │                            │
           ▼                            ▼                            ▼
   1. Text Chunker              1. Query Embedder            1. Keyword Matcher
  (pipeline/chunker.py)       (pipeline/embedder.py)      (pipeline/keyword_search.py)
           │                            │                            │
           ▼                            ▼                            ▼
   2. Local Embedder            2. ChromaDB Query            2. Semantic Search
  (all-MiniLM-L6-v2)             (Cosine Distance)           (Side-by-side run)
           │                            │                            │
           ▼                            ▼                            ▼
   3. ChromaDB Store            3. Re-Ranking Formula        3. Comparative View
  (data/chroma_db)           (Similarity+Recency+Freq)               │
                                        │                            │
                                        ▼                            ▼
                                4. Synthesis Engine ─────────────────┘
                             (Claude API or Local Offline)
```

---

## 4. In-Depth Pipeline Walkthrough

### Stage 1: Document Chunking (`pipeline/chunker.py`)
* Raw documents (`.txt`, `.md`, or pasted text) cannot be embedded as single massive blobs because embeddings lose granular meaning over long texts.
* The system breaks text into overlapping chunks:
  * **Target Size:** ~120 to 150 words per chunk.
  * **Overlap:** 20 words shared between adjacent chunks.
* **Why overlap?** Overlap prevents concepts that occur near chunk boundaries from being split and lost in vector space.

### Stage 2: Vector Embedding Generation (`pipeline/embedder.py`)
* Utilizes the pre-trained `all-MiniLM-L6-v2` transformer model locally.
* Converts every text chunk into a **384-dimensional dense floating-point vector**:
  $$\vec{v} = [x_1, x_2, x_3, \dots, x_{384}]$$
* Normalizes embeddings to unit length ($\|\vec{v}\| = 1.0$), enabling fast dot-product cosine similarity calculation.

### Stage 3: Persistent Vector Storage (`pipeline/vector_store.py`)
* Chunks and their embeddings are saved into a persistent ChromaDB collection (`memory_collection`) stored on disk under `data/chroma_db/`.
* Each record stores:
  * `id`: Deterministic hash (`{source}_{chunk_index}`)
  * `document`: The original chunk text
  * `embedding`: The 384-dimensional float array
  * `metadata`:
    * `source`: Filename or title
    * `chunk_index`: Integer position in document
    * `upload_ts`: Timestamp of ingestion
    * `retrieval_count`: How many times this memory has been surfaced
    * `last_retrieved`: Timestamp of last access

### Stage 4: Semantic Query & Dynamic Re-Ranking
When a user searches for a query (e.g., *"coping with anxiety"*):
1. **Query Vector:** The query string is converted to a 384-dim vector using `embed_query()`.
2. **Cosine Distance Retrieval:** ChromaDB calculates cosine distance against stored vectors:
   $$\text{Similarity} = 1.0 - \frac{\text{Distance}}{2.0}$$
3. **Smart Re-Ranking Formula:**
   Raw similarity isn't enough for personal memory—recent memories and frequently reinforced memories matter more. The system re-ranks candidates using:
   $$\text{Final Score} = 0.70 \times \text{Similarity} + 0.15 \times \text{Recency} + 0.15 \times \text{Frequency}$$
   * **Recency Score:** Exponential decay based on days since upload ($\exp(-\lambda \cdot \Delta t)$).
   * **Frequency Score:** Logarithmic saturation based on previous retrieval count ($\min(1.0, \log(1 + N) / \log(10))$).
4. **Stats Update:** When chunks are retrieved, their `retrieval_count` and `last_retrieved` metadata are automatically updated in ChromaDB.

### Stage 5: Hybrid Answer Synthesis (`pipeline/rag.py`)
The system provides two synthesis modes:
* **Mode A: Cloud Claude 3.5 RAG**
  * Retains strict guardrails: instructed to answer using *only* the retrieved memories and cite sources explicitly.
* **Mode B: Local Extractive Engine (100% Free & Offline)**
  * When no API key is provided, or when Claude API credits are depleted, the system switches to `generate_local_summary()`.
  * Analyzes lexical and semantic overlap between query tokens and retrieved chunk sentences.
  * Formats a structured digest with source citations and relevance percentages without making any external API calls.

---

## 5. REST API Reference

### 1. `POST /api/ingest/`
* **Purpose:** Upload and index new documents into ChromaDB.
* **Content-Type:** `multipart/form-data` or `application/json`
* **Parameters:**
  * `file` *(optional)*: File upload (`.txt` or `.md`)
  * `text` *(optional)*: Raw text string
  * `name` *(optional)*: Document identifier
* **Response:**
  ```json
  {
    "status": "ok",
    "source": "travel_memories.txt",
    "chunks_added": 22,
    "total_chunks": 118
  }
  ```

### 2. `POST /api/query/`
* **Purpose:** Semantic vector retrieval with re-ranking and RAG synthesis.
* **Content-Type:** `application/json`
* **Parameters:**
  * `query`: Search phrase (string)
  * `top_k`: Number of chunks to retrieve (1–10)
  * `source_filter`: *(optional)* Filter to a specific document name
  * `engine`: `"auto"`, `"local"`, or `"claude"`
  * `api_key`: *(optional)* Anthropic API key
  * `model`: *(optional)* Claude model name
* **Response:**
  ```json
  {
    "query": "hiking in the mountains",
    "results": [
      {
        "text": "Then the mountains appeared...",
        "source": "travel_memories.txt",
        "similarity": 0.715,
        "final_score": 0.682,
        "recency": 0.95,
        "frequency": 0.12,
        "retrieved_n": 3
      }
    ],
    "answer": "Synthesized summary...",
    "usage": { "model": "Local Extractive Engine", "input_tokens": 0, "output_tokens": 45 }
  }
  ```

### 3. `POST /api/compare/`
* **Purpose:** Side-by-side benchmark of naive keyword search vs. semantic search on the same query.
* **Response:** Returns `{ "keyword": [...], "semantic": [...], "answer": "..." }`.

### 4. `GET /api/library/` & `DELETE /api/library/<source>/`
* **Purpose:** Inspect all indexed files, chunk counts, access frequencies, and delete document sources from the vector store.

---

## 6. How to Run the Project Locally

### Prerequisites
* Python 3.10+
* Virtual environment (`.venv`)

### Commands
```powershell
# 1. Activate virtual environment
.venv\Scripts\Activate.ps1

# 2. Run database checks
python manage.py check

# 3. Start the Django development server
python manage.py runserver 8000
```
Open **`http://127.0.0.1:8000/`** in any web browser.

---

## 7. Common Presentation & Viva Questions (Study Guide)

### Q1: Why use an embedding model instead of Elasticsearch or SQL `LIKE '%query%'`?
> **Answer:** SQL `LIKE` and Elasticsearch match exact character sequences or stems. If your journal says *"I felt overwhelmed and anxious"*, a search for *"worried about the future"* will return **0 results** in keyword search. Vector embeddings represent conceptual and emotional meaning in 384-dimensional space, capturing synonyms and context automatically.

### Q2: Why is ChromaDB used instead of storing vectors in SQLite or PostgreSQL with pgvector?
> **Answer:** ChromaDB is a lightweight, embedded vector database specifically designed for local AI applications. It requires no separate daemon or server installation, persists directly to disk via SQLite and HNSW (Hierarchical Navigable Small World graphs), and provides native vector distance querying in Python with microsecond latency.

### Q3: What happens if Anthropic/Claude API credits run out?
> **Answer:** 90% of the system (chunking, local embeddings, vector storage, semantic search, and re-ranking) runs 100% locally and never uses credits. If credits run out, the backend gracefully catches the API exception and activates the built-in **Local Extractive Synthesis Engine**, generating a structured digest of matching passages without any cloud calls.

### Q4: How does the memory re-ranking formula work?
> **Answer:** The system uses a weighted formula:
> $$\text{Score} = 0.70 \times \text{SemanticSimilarity} + 0.15 \times \text{Recency} + 0.15 \times \text{Frequency}$$
> This prevents older, stale documents from always outranking fresh memories, and rewards frequently accessed memories through a retrieval count boost.

### Q5: How is the application secured?
> **Answer:** Ingestion runs locally on machine memory. The user's Anthropic API key is stored only in the browser's `localStorage` and sent directly per-request, never persisted in plain text on the server or in the database.
