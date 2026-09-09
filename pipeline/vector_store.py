"""
pipeline/vector_store.py
------------------------
Stage 3 of the pipeline: Persistent Vector Storage with ChromaDB

ChromaDB stores:
  - The raw chunk text as the "document"
  - The real sentence-transformer embedding as the vector
  - Metadata: source filename, upload timestamp, chunk index,
    retrieval_count (how many times this chunk was returned),
    last_retrieved timestamp.

All data is written to disk at ./chroma_db/ and survives restarts.
"""

from __future__ import annotations

import time
import math
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings

# ── ChromaDB persistent client ────────────────────────────────────────────────
DB_PATH        = "./chroma_db"
COLLECTION_NAME = "memories"


def _get_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client writing to ./chroma_db/."""
    return chromadb.PersistentClient(path=DB_PATH)


def get_collection() -> chromadb.Collection:
    """
    Return (or create) the 'memories' collection.
    Uses cosine distance metric so similarity ∈ [0, 1] after normalisation.
    """
    client = _get_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ── Ingestion ─────────────────────────────────────────────────────────────────

def add_documents(
    chunks: list[dict],          # list of {"text": str, "chunk_index": int}
    embeddings: list[list[float]], # one per chunk
    source: str,                  # filename or "pasted_text"
    upload_ts: float | None = None,
) -> int:
    """
    Store chunks + embeddings + metadata in ChromaDB.

    Returns
    -------
    int
        Number of chunks actually added.
    """
    if upload_ts is None:
        upload_ts = time.time()

    collection = get_collection()
    ids, docs, metas, embeds = [], [], [], []

    for chunk, emb in zip(chunks, embeddings):
        doc_id = str(uuid.uuid4())
        ids.append(doc_id)
        docs.append(chunk["text"])
        embeds.append(emb)
        metas.append({
            "source":          source,
            "upload_ts":       upload_ts,
            "chunk_index":     chunk["chunk_index"],
            "retrieval_count": 0,
            "last_retrieved":  0.0,
        })

    collection.add(ids=ids, documents=docs, embeddings=embeds, metadatas=metas)
    return len(ids)


# ── Semantic Search ───────────────────────────────────────────────────────────

def semantic_search(
    query_embedding: list[float],
    top_k: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    """
    Nearest-neighbour search in ChromaDB.

    Parameters
    ----------
    query_embedding : list[float]
        384-dim query vector.
    top_k : int
        Number of results to return before re-ranking.
    source_filter : str, optional
        If set, restrict search to documents from this source.

    Returns
    -------
    list[dict]
        Each dict contains: id, text, metadata, distance, similarity.
    """
    collection = get_collection()
    where = {"source": source_filter} if source_filter else None

    count = collection.count()
    if count == 0:
        return []
    n_fetch = min(top_k * 2, count)  # never request more than what exists

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_fetch,
        where=where,
        include=["documents", "metadatas", "distances", "embeddings"],
    )

    if not results["ids"] or not results["ids"][0]:
        return []

    now = time.time()
    items = []
    for doc_id, text, meta, dist in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB cosine distance ∈ [0, 2]; convert to similarity ∈ [0, 1]
        similarity = 1.0 - dist / 2.0

        # ── Re-ranking signals (all from real stored metadata) ──────────────
        # Recency bonus: recent docs score higher (normalised 0→1 over 30 days)
        age_seconds    = now - float(meta.get("upload_ts", now))
        recency_bonus  = max(0.0, 1.0 - age_seconds / (30 * 86400))

        # Frequency bonus: logarithmic dampening of retrieval count
        retrieval_ct   = int(meta.get("retrieval_count", 0))
        freq_bonus     = math.log1p(retrieval_ct) / math.log1p(100)  # normalised

        # Weighted composite score
        final_score = (similarity * 0.75) + (recency_bonus * 0.15) + (freq_bonus * 0.10)

        items.append({
            "id":          doc_id,
            "text":        text,
            "metadata":    meta,
            "distance":    round(dist, 4),
            "similarity":  round(similarity, 4),
            "recency":     round(recency_bonus, 4),
            "frequency":   round(freq_bonus, 4),
            "final_score": round(final_score, 4),
        })

    # Sort by composite score, return top_k
    items.sort(key=lambda x: x["final_score"], reverse=True)
    return items[:top_k]


def update_retrieval_stats(doc_ids: list[str]) -> None:
    """
    Increment retrieval_count and update last_retrieved for returned chunks.
    Called every time results are shown to the user.
    """
    collection = get_collection()
    now = time.time()

    for doc_id in doc_ids:
        results = collection.get(ids=[doc_id], include=["metadatas"])
        if not results["ids"]:
            continue
        meta = results["metadatas"][0]
        meta["retrieval_count"] = int(meta.get("retrieval_count", 0)) + 1
        meta["last_retrieved"]  = now
        collection.update(ids=[doc_id], metadatas=[meta])


# ── Source Management ─────────────────────────────────────────────────────────

def list_sources() -> list[dict]:
    """
    Return a summary of all ingested sources with their stats.
    """
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    # Fetch all metadata (no embeddings needed)
    all_data = collection.get(include=["metadatas"])
    sources: dict[str, dict] = {}
    for meta in all_data["metadatas"]:
        src = meta.get("source", "unknown")
        if src not in sources:
            sources[src] = {
                "source":          src,
                "chunk_count":     0,
                "total_retrieved": 0,
                "upload_ts":       meta.get("upload_ts", 0),
            }
        sources[src]["chunk_count"]     += 1
        sources[src]["total_retrieved"] += int(meta.get("retrieval_count", 0))

    return list(sources.values())


def delete_source(source: str) -> int:
    """Delete all chunks belonging to a source. Returns count deleted."""
    collection = get_collection()
    results = collection.get(where={"source": source})
    ids = results["ids"]
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def collection_count() -> int:
    """Return total number of stored chunks."""
    return get_collection().count()
