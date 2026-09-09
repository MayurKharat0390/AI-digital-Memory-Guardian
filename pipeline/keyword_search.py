"""
pipeline/keyword_search.py
--------------------------
Naive Keyword Search (for comparison against semantic search)

Implements a simple TF-style term-frequency scoring:
  - Tokenise query and each stored chunk into lowercase words
  - Score each chunk by how many query terms it contains (weighted by frequency)
  - No embeddings, no vectors — pure string matching

This is intentionally "dumb" to demonstrate the superiority of
semantic search on natural-language queries.
"""

from __future__ import annotations

import re
from collections import Counter

from pipeline.vector_store import get_collection


def _tokenise(text: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [w for w in text.split() if len(w) > 1]


def keyword_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Score every stored chunk by naive term-frequency keyword matching.

    Parameters
    ----------
    query : str
        Natural language query.
    top_k : int
        Number of top results to return.

    Returns
    -------
    list[dict]
        Each dict: {text, metadata, kw_score, matched_terms}
    """
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    # Fetch ALL stored chunks (text + metadata only, no embeddings)
    all_data = collection.get(include=["documents", "metadatas"])

    query_tokens = _tokenise(query)
    query_set    = set(query_tokens)
    query_counts = Counter(query_tokens)

    results = []
    for text, meta in zip(all_data["documents"], all_data["metadatas"]):
        chunk_tokens  = _tokenise(text)
        chunk_counter = Counter(chunk_tokens)

        # Term frequency: sum of min(query_freq, chunk_freq) for each matching term
        matched_terms = []
        score = 0.0
        for term in query_set:
            if chunk_counter[term] > 0:
                score += min(query_counts[term], chunk_counter[term])
                matched_terms.append(term)

        # Normalise by query length so score ∈ [0, 1]
        if query_tokens:
            score = score / len(query_tokens)

        results.append({
            "text":          text,
            "metadata":      meta,
            "kw_score":      round(score, 4),
            "matched_terms": matched_terms,
        })

    # Sort descending by score, return top_k (only include results with score > 0)
    results.sort(key=lambda x: x["kw_score"], reverse=True)
    results = [r for r in results if r["kw_score"] > 0]
    return results[:top_k]
