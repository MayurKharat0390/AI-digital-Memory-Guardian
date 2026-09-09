"""
pipeline/chunker.py
-------------------
Stage 1 of the ingestion pipeline: Text Chunking

Strategy:
  1. Split by paragraph boundaries (double newline).
  2. If a paragraph exceeds MAX_CHARS, apply a sliding-window
     sub-chunker (chunk_size chars, overlap chars).

Returns a flat list of chunk dicts:
  {"text": str, "chunk_index": int}
"""

from __future__ import annotations

MAX_CHARS = 512   # characters before sub-chunking kicks in
OVERLAP   = 64    # character overlap between sub-chunks


def _sliding_window(text: str, chunk_size: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Split a long string into overlapping windows."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap  # slide back by overlap amount
    return [c for c in chunks if c]  # drop empty strings


def chunk_text(text: str) -> list[dict]:
    """
    Main entry point.

    Parameters
    ----------
    text : str
        Raw document text.

    Returns
    -------
    list[dict]
        Each dict: {"text": str, "chunk_index": int}
    """
    # Normalise line endings, then split on blank lines
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    paragraphs = [p for p in paragraphs if p]  # remove empty

    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= MAX_CHARS:
            chunks.append(para)
        else:
            # Sub-chunk long paragraphs with sliding window
            chunks.extend(_sliding_window(para))

    return [{"text": chunk, "chunk_index": i} for i, chunk in enumerate(chunks)]
