"""
pipeline/embedder.py
--------------------
Stage 2 of the ingestion pipeline: Embedding Generation

Uses the 'all-MiniLM-L6-v2' sentence-transformer model running
LOCALLY (no API call, no internet required after first download).

The model produces real 384-dimensional dense vectors.
Cached as a Streamlit resource so it is only loaded once per session.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

# ── Model is downloaded once to HuggingFace cache (~22 MB) ──────────────────
MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """
    Return a singleton SentenceTransformer model instance.
    Call this from Streamlit with @st.cache_resource instead to avoid
    re-loading the model on every rerun.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: list[str], model: SentenceTransformer | None = None) -> np.ndarray:
    """
    Embed a list of strings into real 384-dim vectors.

    Parameters
    ----------
    texts : list[str]
        Strings to encode.
    model : SentenceTransformer, optional
        Pre-loaded model. If None, loads via get_model().

    Returns
    -------
    np.ndarray
        Shape (N, 384) — one row per input text.
    """
    if model is None:
        model = get_model()
    # show_progress_bar=False keeps Streamlit output clean
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return np.array(embeddings, dtype=np.float32)


def embed_query(query: str, model: SentenceTransformer | None = None) -> list[float]:
    """
    Embed a single query string and return as a Python list (ChromaDB format).
    """
    vec = embed_texts([query], model=model)[0]
    return vec.tolist()
